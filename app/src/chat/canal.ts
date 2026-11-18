/**
 * Canal en vivo del chat (/ws/chat/, CC-19). Avisa de mensajes, lecturas y cambios de conversaciones; la app vuelve
 * a pedir lo que muestra. Reconexión y renovación del access, igual que el canal de viajes (HU-14).
 */

import type { CrearSocket, SocketMinimo } from '../conductor/canal';
import { SinRed, type SesionApp } from '../sesion/sesion';

export interface MensajeChat {
  id: number;
  conversacion: number;
  texto: string;
  rapida: string;
  autor: string;
  propio: boolean;
  creado_en: string;
}

export type EventoChat =
  | { tipo: 'inicial' }
  | { tipo: 'mensaje'; mensaje: MensajeChat }
  | { tipo: 'leido'; conversacion: number }
  | { tipo: 'conversaciones' }
  | { tipo: 'pong' };

const SIN_SESION = 4401;
const ESPERA_MAXIMA_MS = 30_000;

export function urlDelChat(base: string): string {
  const origen = base || (typeof location !== 'undefined' ? location.origin : '');
  return `${origen.replace(/^http/, 'ws')}/ws/chat/`;
}

export class CanalChat {
  private socket: SocketMinimo | null = null;
  private intentos = 0;
  private espera: ReturnType<typeof setTimeout> | null = null;
  private activo = false;
  private oyentes = new Set<(evento: EventoChat) => void>();

  constructor(
    private readonly url: string,
    private readonly sesion: Pick<SesionApp, 'access' | 'renovar'>,
    private readonly crearSocket: CrearSocket = (url, p) => new WebSocket(url, p) as unknown as SocketMinimo,
  ) {}

  alEvento(oyente: (evento: EventoChat) => void): () => void {
    this.oyentes.add(oyente);
    return () => this.oyentes.delete(oyente);
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
    };
    socket.onmessage = (evento) => {
      const datos = JSON.parse(evento.data) as EventoChat;
      if (datos.tipo !== 'pong') this.oyentes.forEach((oyente) => oyente(datos));
    };
    socket.onclose = (evento) => {
      if (this.socket !== socket || !this.activo) return;
      this.socket = null;
      if (evento.code === SIN_SESION) void this.conectar(true);
      else this.reintentar();
    };
  }
}
