/**
 * Canal en vivo del conductor (/ws/conductor/, HU-14): recibe el viaje asignado mientras la app está abierta o en
 * segundo plano (el WebView no se suspende gracias al ajuste de MainActivity, H-3).
 *
 * - El access viaja como subprotocolo. Ante el cierre 4401 renueva (operación compartida de la sesión) y se
 *   reconecta; otros cierres, con espera creciente hasta 30 s.
 * - Al conectarse, el backend reenvía la asignación que espera respuesta: si la app estuvo sin red, no se pierde.
 */

import { SinRed, type SesionApp } from '../sesion/sesion';

export interface Punto {
  direccion: string;
  lat: number;
  lon: number;
}

export interface Asignacion {
  asignacion: number;
  viaje: number;
  pasajero: string;
  origen: Punto;
  destino: Punto;
  recogida_en: string;
  tarifa: number | null;
  vuelo: { numero: string; hora_programada: string; hora_estimada: string | null } | null;
  vence_en: string;
}

type Mensaje =
  | { tipo: 'asignado'; asignacion: Asignacion }
  | { tipo: 'sin_asignacion'; asignacion: number }
  | { tipo: 'viaje'; viaje: number }
  | { tipo: 'pong' };

export interface SocketMinimo {
  onopen: (() => void) | null;
  onmessage: ((evento: { data: string }) => void) | null;
  onclose: ((evento: { code: number }) => void) | null;
  close(): void;
}

export type CrearSocket = (url: string, protocolos: string[]) => SocketMinimo;

export interface EstadoCanal {
  conectado: boolean;
  asignacion: Asignacion | null;
}

const SIN_SESION = 4401;
const ESPERA_MAXIMA_MS = 30_000;

export function urlDelCanal(base: string): string {
  // Sin base (navegador con el proxy de Vite) se usa el origen de la página.
  const origen = base || (typeof location !== 'undefined' ? location.origin : '');
  return `${origen.replace(/^http/, 'ws')}/ws/conductor/`;
}

export class CanalConductor {
  private socket: SocketMinimo | null = null;
  private intentos = 0;
  private espera: ReturnType<typeof setTimeout> | null = null;
  private activo = false;
  private estadoActual: EstadoCanal = { conectado: false, asignacion: null };
  private oyentes = new Set<(estado: EstadoCanal) => void>();
  private alAsignar = new Set<(asignacion: Asignacion) => void>();
  private alCambiar = new Set<() => void>();

  constructor(
    private readonly url: string,
    private readonly sesion: Pick<SesionApp, 'access' | 'renovar'>,
    private readonly crearSocket: CrearSocket = (url, p) => new WebSocket(url, p) as unknown as SocketMinimo,
  ) {}

  get estado(): EstadoCanal {
    return this.estadoActual;
  }

  suscribir(oyente: (estado: EstadoCanal) => void): () => void {
    this.oyentes.add(oyente);
    oyente(this.estadoActual);
    return () => this.oyentes.delete(oyente);
  }

  /** Se llama una vez por cada asignación nueva (para la alerta sonora y la notificación). */
  alRecibirAsignacion(oyente: (asignacion: Asignacion) => void): () => void {
    this.alAsignar.add(oyente);
    return () => this.alAsignar.delete(oyente);
  }

  /** El viaje cambió sin que lo pidiera la app (EN_ZONA automático, cancelación desde el panel). */
  alCambiarViaje(oyente: () => void): () => void {
    this.alCambiar.add(oyente);
    return () => this.alCambiar.delete(oyente);
  }

  private publicar(cambios: Partial<EstadoCanal>) {
    this.estadoActual = { ...this.estadoActual, ...cambios };
    this.oyentes.forEach((oyente) => oyente(this.estadoActual));
  }

  iniciar() {
    if (this.activo) return;
    this.activo = true;
    void this.conectar(false);
  }

  detener() {
    this.activo = false;
    if (this.espera) clearTimeout(this.espera);
    this.socket?.close();
    this.socket = null;
    this.publicar({ conectado: false, asignacion: null });
  }

  /** La app terminó con la asignación (respondió o venció): deja de mostrarla. */
  olvidar(id: number) {
    if (this.estadoActual.asignacion?.asignacion === id) this.publicar({ asignacion: null });
  }

  private reintentar() {
    const espera = Math.min(ESPERA_MAXIMA_MS, 1000 * 2 ** this.intentos);
    this.intentos += 1;
    this.espera = setTimeout(() => void this.conectar(false), espera);
  }

  private async conectar(renovar: boolean) {
    let access: string | null;
    try {
      access = renovar ? await this.sesion.renovar() : this.sesion.access ?? (await this.sesion.renovar());
    } catch (error) {
      if (error instanceof SinRed && this.activo) this.reintentar();
      return;
    }
    if (!this.activo || !access) return;
    const socket = this.crearSocket(this.url, ['flotaagil', access]);
    this.socket = socket;
    socket.onopen = () => {
      this.intentos = 0;
      this.publicar({ conectado: true });
    };
    socket.onmessage = (evento) => this.recibir(JSON.parse(evento.data) as Mensaje);
    socket.onclose = (evento) => {
      if (this.socket !== socket || !this.activo) return;
      this.socket = null;
      this.publicar({ conectado: false });
      if (evento.code === SIN_SESION) void this.conectar(true);
      else this.reintentar();
    };
  }

  private recibir(mensaje: Mensaje) {
    if (mensaje.tipo === 'asignado') {
      const nueva = this.estadoActual.asignacion?.asignacion !== mensaje.asignacion.asignacion;
      this.publicar({ asignacion: mensaje.asignacion });
      if (nueva) this.alAsignar.forEach((oyente) => oyente(mensaje.asignacion));
    }
    if (mensaje.tipo === 'sin_asignacion') this.olvidar(mensaje.asignacion);
    if (mensaje.tipo === 'viaje') this.alCambiar.forEach((oyente) => oyente());
  }
}

/** Segundos que quedan para responder (RN-04), nunca negativos. */
export function segundosRestantes(venceEn: string, ahora: number): number {
  return Math.max(0, Math.ceil((Date.parse(venceEn) - ahora) / 1000));
}
