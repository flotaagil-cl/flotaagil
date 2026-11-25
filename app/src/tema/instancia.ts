/** El tema de este celular, armado una sola vez: lo alimenta la sesión (servicios.ts) y lo leen las pantallas. */

import { API_URL } from '../apiUrl';
import { descargarImagen } from './descargar';
import { TemaApp } from './tema';

export const temaApp = new TemaApp(globalThis.localStorage ?? null, descargarImagen, API_URL);
