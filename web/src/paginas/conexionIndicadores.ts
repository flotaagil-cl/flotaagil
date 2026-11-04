/**
 * /ws/indicadores/ (HU-01): solo avisa que algo cambió, y los números se vuelven a pedir por la API. Al conectarse o
 * reconectarse también avisa, por si se perdió un cambio. Reconexión y renovación del access, igual que el mapa.
 */

import type { CrearSocket, SesionParaMapa, SocketMinimo } from '../mapa/conexion';

export type FaseIndicadores = 'conectando' | 'en_vivo' | 'reconectando' | 'sin_sesion';

const SIN_SESION = 4401;
const ESPERA_MAXIMA_MS = 30_000;

export class ConexionIndicadores {
  private socket: SocketMinimo | null = null;
  private intentos = 0;
  private espera: ReturnType<typeof setTimeout> | null = null;
  private detenida = false;

  constructor(
    private readonly url: string,
    private readonly sesion: SesionParaMapa,
    private readonly alCambiar: () => void,
    private readonly alCambiarFase: (fase: FaseIndicadores) => void,
    private readonly crearSocket: CrearSocket = (url, protocolos) => new WebSocket(url, protocolos) as unknown as SocketMinimo,
  ) {}

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
      this.alCambiarFase('sin_sesion');
      return;
    }
    const socket = this.crearSocket(this.url, ['flotaagil', access]);
    this.socket = socket;
    socket.onopen = () => {
      this.intentos = 0;
      this.alCambiarFase('en_vivo');
    };
    socket.onmessage = () => this.alCambiar();
    socket.onclose = (evento) => {
      if (this.socket !== socket || this.detenida) return;
      this.socket = null;
      this.alCambiarFase('reconectando');
      if (evento.code === SIN_SESION) {
        void this.conectar(true);
        return;
      }
      const espera = Math.min(ESPERA_MAXIMA_MS, 1000 * 2 ** this.intentos);
      this.intentos += 1;
      this.espera = setTimeout(() => void this.conectar(), espera);
    };
  }
}
