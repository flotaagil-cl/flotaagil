/**
 * Conexión al WebSocket del mapa (/ws/mapa/, HU-02).
 *
 * - El access viaja como subprotocolo (`["flotaagil", access]`): el navegador no permite encabezados y en la URL
 *   quedaría en los logs.
 * - Cierre 4401 (sin sesión o access vencido): renueva con la operación compartida de la pestaña y se reconecta;
 *   si la sesión terminó, queda en «sin_sesion» (la guarda del panel lleva al login).
 * - Cualquier otro cierre: se reconecta con espera creciente (1 s, 2 s, 4 s… hasta 30 s).
 * - Cada reconexión recibe la foto inicial completa, así que no se pierden cambios.
 */

import { aplicar, type ConductorMapa, type Mensaje } from './estado';

export interface SocketMinimo {
  onopen: (() => void) | null;
  onmessage: ((evento: { data: string }) => void) | null;
  onclose: ((evento: { code: number }) => void) | null;
  close(): void;
}

export type CrearSocket = (url: string, protocolos: string[]) => SocketMinimo;

export interface SesionParaMapa {
  access(): string | null;
  renovarTrasRechazo(): Promise<string | null>;
}

export type FaseConexion = 'conectando' | 'conectado' | 'reconectando' | 'sin_sesion';

export interface EstadoMapa {
  fase: FaseConexion;
  conductores: Map<number, ConductorMapa>;
  /** Cuándo se recibió (ms) la última posición de cada conductor: sirve para medir la latencia. */
  recibidas: Map<number, number>;
}

export const SIN_SESION = 4401;
const ESPERA_MAXIMA_MS = 30_000;

export function urlDelMapa(origen: string): string {
  return `${origen.replace(/^http/, 'ws')}/ws/mapa/`;
}

export class ConexionMapa {
  private socket: SocketMinimo | null = null;
  private intentos = 0;
  private espera: ReturnType<typeof setTimeout> | null = null;
  private detenida = false;
  private estadoActual: EstadoMapa = { fase: 'conectando', conductores: new Map(), recibidas: new Map() };
  private oyentes = new Set<(estado: EstadoMapa) => void>();

  constructor(
    private readonly url: string,
    private readonly sesion: SesionParaMapa,
    // El WebSocket del navegador cumple SocketMinimo (solo se usan esos manejadores y close).
    private readonly crearSocket: CrearSocket = (url, protocolos) => new WebSocket(url, protocolos) as unknown as SocketMinimo,
    private readonly ahora: () => number = Date.now,
  ) {}

  get estado(): EstadoMapa {
    return this.estadoActual;
  }

  suscribir(oyente: (estado: EstadoMapa) => void): () => void {
    this.oyentes.add(oyente);
    oyente(this.estadoActual);
    return () => this.oyentes.delete(oyente);
  }

  private publicar(cambios: Partial<EstadoMapa>) {
    this.estadoActual = { ...this.estadoActual, ...cambios };
    this.oyentes.forEach((oyente) => oyente(this.estadoActual));
  }

  iniciar() {
    this.detenida = false;
    void this.conectar();
  }

  detener() {
    this.detenida = true;
    if (this.espera) clearTimeout(this.espera);
    this.socket?.close();
    this.socket = null;
  }

  private async conectar(renovar = false) {
    const access = renovar ? await this.sesion.renovarTrasRechazo() : this.sesion.access() ?? (await this.sesion.renovarTrasRechazo());
    if (this.detenida) return;
    if (!access) {
      this.publicar({ fase: 'sin_sesion' });
      return;
    }
    const socket = this.crearSocket(this.url, ['flotaagil', access]);
    this.socket = socket;
    socket.onopen = () => {
      this.intentos = 0;
      this.publicar({ fase: 'conectado' });
    };
    socket.onmessage = (evento) => this.recibir(JSON.parse(evento.data) as Mensaje);
    socket.onclose = (evento) => {
      if (this.socket !== socket || this.detenida) return;
      this.socket = null;
      if (evento.code === SIN_SESION) {
        this.publicar({ fase: 'reconectando' });
        void this.conectar(true);
        return;
      }
      this.publicar({ fase: 'reconectando' });
      const espera = Math.min(ESPERA_MAXIMA_MS, 1000 * 2 ** this.intentos);
      this.intentos += 1;
      this.espera = setTimeout(() => void this.conectar(), espera);
    };
  }

  private recibir(mensaje: Mensaje) {
    if (mensaje.tipo === 'pong') return;
    const recibidas = new Map(this.estadoActual.recibidas);
    const ahora = this.ahora();
    if (mensaje.tipo === 'inicial') mensaje.conductores.forEach((c) => recibidas.set(c.id, ahora));
    if (mensaje.tipo === 'conductor') recibidas.set(mensaje.conductor.id, ahora);
    if (mensaje.tipo === 'fuera') recibidas.delete(mensaje.id);
    this.publicar({ conductores: aplicar(this.estadoActual.conductores, mensaje), recibidas });
  }
}
