/**
 * Peticiones a la API con la sesión de la app: agrega el access y, ante un 401, renueva (operación compartida)
 * y repite la petición una vez. Un 403 `cambio_password_requerido` deja la sesión pidiendo el cambio.
 */

import { ErrorApi, SinRed, SinSesion, type Http, type SesionApp } from './sesion/sesion';

export class Api {
  constructor(
    private readonly http: Http,
    private readonly sesion: SesionApp,
  ) {}

  private async enviar(metodo: string, ruta: string, cuerpo: unknown, access: string): Promise<Response> {
    try {
      return await this.http(`${this.sesion.base}${ruta}`, {
        method: metodo,
        headers: {
          Authorization: `Bearer ${access}`,
          ...(cuerpo === undefined ? {} : { 'Content-Type': 'application/json' }),
        },
        ...(cuerpo === undefined ? {} : { body: JSON.stringify(cuerpo) }),
      });
    } catch {
      throw new SinRed();
    }
  }

  /** Devuelve el JSON de una respuesta 2xx. Lanza ErrorApi, SinRed o SinSesion. */
  async pedir<T>(metodo: 'GET' | 'POST', ruta: string, cuerpo?: unknown): Promise<T> {
    let access = this.sesion.access ?? (await this.sesion.renovar());
    if (!access) throw new SinSesion();
    let respuesta = await this.enviar(metodo, ruta, cuerpo, access);
    if (respuesta.status === 401) {
      access = await this.sesion.renovar();
      if (!access) throw new SinSesion();
      respuesta = await this.enviar(metodo, ruta, cuerpo, access);
    }
    let datos: Record<string, unknown> | null = null;
    try {
      datos = (await respuesta.json()) as Record<string, unknown>;
    } catch {
      // Sin cuerpo JSON (p. ej. 502 del proxy).
    }
    if (respuesta.ok) return datos as T;
    const error = new ErrorApi(respuesta.status, datos);
    if (respuesta.status === 401) throw new SinSesion();
    if (error.codigo === 'cambio_password_requerido') this.sesion.marcarCambioPendiente();
    throw error;
  }
}
