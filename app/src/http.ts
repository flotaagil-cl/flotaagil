/**
 * Tiempo límite de todas las peticiones de la app (10 s). Sin él, una respuesta que no llega deja la pantalla
 * esperando para siempre (HU-16, `docs/evidencias/HU-16/resultados.md`).
 *
 * Además de abortar con AbortController, compite contra un temporizador: así no depende de que el fetch nativo de
 * CapacitorHttp respete la señal. El cuerpo se lee dentro del plazo, porque también puede quedarse a medias.
 */

import type { Http } from './sesion/sesion';

export const TIEMPO_LIMITE_MS = 10_000;

/** Estados HTTP que no admiten cuerpo al construir un Response. */
const SIN_CUERPO = new Set([101, 204, 205, 304]);

export class TiempoAgotado extends Error {
  constructor() {
    super('La petición superó el tiempo límite.');
    this.name = 'TiempoAgotado';
  }
}

export function conTiempoLimite(http: Http, limiteMs: number = TIEMPO_LIMITE_MS): Http {
  return async (url, init) => {
    const control = new AbortController();
    let reloj: ReturnType<typeof setTimeout> | undefined;
    const vencimiento = new Promise<never>((_, rechazar) => {
      reloj = setTimeout(() => {
        control.abort();
        rechazar(new TiempoAgotado());
      }, limiteMs);
    });
    const completa = async () => {
      const respuesta = await http(url, { ...init, signal: control.signal });
      const cuerpo = await respuesta.text();
      return new Response(SIN_CUERPO.has(respuesta.status) ? null : cuerpo, {
        status: respuesta.status,
        statusText: respuesta.statusText,
        headers: respuesta.headers,
      });
    };
    try {
      return await Promise.race([completa(), vencimiento]);
    } finally {
      clearTimeout(reloj);
    }
  };
}
