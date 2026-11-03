/**
 * Cola de posiciones por enviar a POST /api/app/posiciones/.
 *
 * - Cada posición registrada se intenta enviar de inmediato (latencia del mapa, HU-02), en lotes de hasta 100 si
 *   hay atraso.
 * - Un access vencido no corta el envío: Api renueva y repite. Sin red o con 5xx, las posiciones se quedan en la
 *   cola y se reintentan en el siguiente envío (con espera creciente hasta 60 s). El reenvío de un lote que sí
 *   llegó no duplica: el backend las identifica por conductor e instante (DC-15).
 * - Si el backend responde que el conductor no está en turno o no dio su consentimiento (RN-18), se vacía la cola
 *   y se avisa para detener el GPS.
 * - La cola vive en memoria (no se guardan posiciones en el teléfono): máximo MAX_PENDIENTES, se descartan las
 *   más antiguas.
 */

import type { Api } from '../api';
import { ErrorApi, SinSesion } from '../sesion/sesion';

export interface PosicionApp {
  lat: number;
  lon: number;
  precision_m: number | null;
  registrada_en: string;
}

export const MAX_POR_LOTE = 100;
/** ~5,5 h de atraso en viaje (una cada 10 s) o ~16 h en espera. */
export const MAX_PENDIENTES = 2000;
const ESPERA_MAXIMA_MS = 60_000;

export interface EstadoEnvio {
  pendientes: number;
  ultimoEnvio: string | null;
  error: 'sin_conexion' | 'sin_sesion' | null;
  detenido: 'fuera_de_turno' | 'sin_consentimiento' | null;
}

export class ColaPosiciones {
  private cola: PosicionApp[] = [];
  private enCurso: Promise<void> | null = null;
  private fallos = 0;
  private noAntesDe = 0;
  private estadoActual: EstadoEnvio = { pendientes: 0, ultimoEnvio: null, error: null, detenido: null };
  private oyentes = new Set<(estado: EstadoEnvio) => void>();

  constructor(
    private readonly api: Api,
    private readonly ahora: () => number = Date.now,
  ) {}

  get estado(): EstadoEnvio {
    return this.estadoActual;
  }

  suscribir(oyente: (estado: EstadoEnvio) => void): () => void {
    this.oyentes.add(oyente);
    oyente(this.estadoActual);
    return () => this.oyentes.delete(oyente);
  }

  private publicar(cambios: Partial<EstadoEnvio>) {
    this.estadoActual = { ...this.estadoActual, ...cambios, pendientes: this.cola.length };
    this.oyentes.forEach((oyente) => oyente(this.estadoActual));
  }

  /** Agrega una posición y dispara el envío (si no hay uno en curso ni una espera por fallos). */
  agregar(posicion: PosicionApp): Promise<void> {
    this.cola.push(posicion);
    if (this.cola.length > MAX_PENDIENTES) this.cola.splice(0, this.cola.length - MAX_PENDIENTES);
    this.publicar({});
    return this.enviar();
  }

  /** Envía lo pendiente, lote a lote. Las llamadas mientras hay un envío en curso esperan ese mismo. */
  enviar(): Promise<void> {
    if (this.enCurso) return this.enCurso;
    if (!this.cola.length || this.ahora() < this.noAntesDe) return Promise.resolve();
    this.enCurso = this.vaciar().finally(() => {
      this.enCurso = null;
    });
    return this.enCurso;
  }

  private async vaciar(): Promise<void> {
    while (this.cola.length) {
      const lote = this.cola.slice(0, MAX_POR_LOTE);
      try {
        await this.api.pedir('POST', '/api/app/posiciones/', { posiciones: lote });
      } catch (error) {
        if (error instanceof ErrorApi && (error.codigo === 'fuera_de_turno' || error.codigo === 'sin_consentimiento')) {
          this.cola = [];
          this.publicar({ detenido: error.codigo, error: null });
          return;
        }
        if (error instanceof ErrorApi && error.estado === 400) {
          // Lote inválido (no debería pasar): se descarta para no bloquear la cola.
          this.cola.splice(0, lote.length);
          continue;
        }
        this.fallos += 1;
        this.noAntesDe = this.ahora() + Math.min(ESPERA_MAXIMA_MS, 2 ** this.fallos * 1000);
        this.publicar({ error: error instanceof SinSesion ? 'sin_sesion' : 'sin_conexion' });
        return;
      }
      this.cola.splice(0, lote.length);
      this.fallos = 0;
      this.noAntesDe = 0;
      this.publicar({ ultimoEnvio: new Date(this.ahora()).toISOString(), error: null, detenido: null });
    }
  }

  /** Al cerrar sesión: nada pendiente debe enviarse con la cuenta de otra persona. */
  vaciarSinEnviar() {
    this.cola = [];
    this.fallos = 0;
    this.noAntesDe = 0;
    this.publicar({ error: null, detenido: null });
  }
}
