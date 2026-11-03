/**
 * Registro de la ubicación durante el turno (RN-18): solo con consentimiento y en estado Disponible o En viaje.
 * Toma una posición cada 10 s en viaje y 30 s en espera (muestreo.ts) y la pone en la cola de envío.
 */

import type { ColaPosiciones } from './envio';
import { debeRegistrar, INTERVALO_OBJETIVO_S, type Modo } from './muestreo';
import type { CallbackError, Location } from './rastreo';

export interface Plugin {
  iniciar(alRecibir: (posicion: Location) => void, alFallar: (error: CallbackError) => void): Promise<string>;
  detener(id: string): Promise<void>;
}

export type EstadoRastreo = { activo: boolean; error: 'permiso' | 'otro' | null };

export class Rastreador {
  private watcher: string | null = null;
  private ultimaMs: number | null = null;
  private modo: Modo = 'espera';
  private estadoActual: EstadoRastreo = { activo: false, error: null };
  private oyentes = new Set<(estado: EstadoRastreo) => void>();

  constructor(
    private readonly plugin: Plugin,
    private readonly cola: ColaPosiciones,
    private readonly ahora: () => number = Date.now,
  ) {}

  get estado() {
    return this.estadoActual;
  }

  suscribir(oyente: (estado: EstadoRastreo) => void): () => void {
    this.oyentes.add(oyente);
    oyente(this.estadoActual);
    return () => this.oyentes.delete(oyente);
  }

  private publicar(estado: EstadoRastreo) {
    this.estadoActual = estado;
    this.oyentes.forEach((oyente) => oyente(estado));
  }

  /** Inicia (si no estaba) con el modo dado; si ya estaba, solo cambia el modo. */
  async iniciar(modo: Modo): Promise<void> {
    this.modo = modo;
    if (this.watcher) return;
    try {
      this.watcher = await this.plugin.iniciar(
        (posicion) => this.recibir(posicion),
        (error) => this.publicar({ activo: false, error: error.code === 'NOT_AUTHORIZED' ? 'permiso' : 'otro' }),
      );
      this.publicar({ activo: true, error: null });
    } catch {
      this.publicar({ activo: false, error: 'otro' });
    }
  }

  async detener(): Promise<void> {
    if (!this.watcher) return;
    const id = this.watcher;
    this.watcher = null;
    this.ultimaMs = null;
    await this.plugin.detener(id);
    this.publicar({ activo: false, error: null });
  }

  private recibir(posicion: Location) {
    const ahora = this.ahora();
    if (!debeRegistrar(this.ultimaMs, ahora, INTERVALO_OBJETIVO_S[this.modo])) return;
    this.ultimaMs = ahora;
    void this.cola.agregar({
      lat: posicion.latitude,
      lon: posicion.longitude,
      precision_m: Number.isFinite(posicion.accuracy) ? Math.round(posicion.accuracy * 10) / 10 : null,
      registrada_en: new Date(posicion.time ?? ahora).toISOString(),
    });
  }
}
