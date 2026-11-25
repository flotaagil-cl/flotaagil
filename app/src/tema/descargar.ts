/**
 * CC-27 (HU-80): descarga del logo. El `fetch` nativo de Capacitor entrega las imágenes como texto y las daña, así
 * que se pide con `CapacitorHttp` y `responseType: 'blob'`, que devuelve base64 en Android y en el navegador.
 */

import { CapacitorHttp } from '@capacitor/core';
import type { DescargarImagen } from './tema';

const ESPERA_MS = 10_000;

export const descargarImagen: DescargarImagen = async (url) => {
  try {
    const respuesta = await CapacitorHttp.request({
      method: 'GET',
      url,
      responseType: 'blob',
      connectTimeout: ESPERA_MS,
      readTimeout: ESPERA_MS,
    });
    const datos: unknown = respuesta.data;
    // El servidor siempre entrega las variantes del logo en PNG.
    return respuesta.status === 200 && typeof datos === 'string' && datos
      ? `data:image/png;base64,${datos.replace(/\s/g, '')}`
      : null;
  } catch {
    return null;
  }
};
