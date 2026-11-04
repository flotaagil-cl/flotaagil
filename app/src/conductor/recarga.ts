/**
 * Mantiene al día lo que muestra la app (perfil y viaje activo):
 * - Gana la última lectura: una respuesta atrasada no pisa a una más nueva.
 * - Si la lectura falla o agota el tiempo, se reintenta sola con espera creciente hasta 30 s, sin que el conductor
 *   tenga que tocar nada. Sin sesión no se reintenta: la app ya vuelve al login.
 */

import { SinSesion } from '../sesion/sesion';

const ESPERA_BASE_MS = 2_000;
const ESPERA_MAXIMA_MS = 30_000;

export class Recarga<T> {
  private turno = 0;
  private fallas = 0;
  private activa = true;
  private reintento: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private readonly leer: () => Promise<T>,
    private readonly aplicar: (datos: T) => void,
    private readonly alFallar: (error: unknown) => void,
  ) {}

  iniciar() {
    this.activa = true;
  }

  detener() {
    this.activa = false;
    this.turno += 1;
    this.limpiar();
  }

  private limpiar() {
    if (this.reintento) clearTimeout(this.reintento);
    this.reintento = null;
  }

  /** Lee ahora. Termina cuando esa lectura acaba, bien o mal; nunca lanza. */
  async recargar(): Promise<void> {
    if (!this.activa) return;
    this.limpiar();
    this.turno += 1;
    const turno = this.turno;
    try {
      const datos = await this.leer();
      if (turno !== this.turno) return;
      this.fallas = 0;
      this.aplicar(datos);
    } catch (error) {
      if (turno !== this.turno) return;
      this.alFallar(error);
      if (error instanceof SinSesion) return;
      const espera = Math.min(ESPERA_MAXIMA_MS, ESPERA_BASE_MS * 2 ** this.fallas);
      this.fallas += 1;
      this.reintento = setTimeout(() => void this.recargar(), espera);
    }
  }
}
