/** Servicios de la app armados una sola vez: sesión, API, cola de envío y rastreador del GPS. */

import { Api } from './api';
import { ColaPosiciones } from './gps/envio';
import { detenerRastreo, iniciarRastreo } from './gps/rastreo';
import { Rastreador } from './gps/turno';
import { almacenSeguro } from './sesion/almacen';
import { SesionApp, type Http } from './sesion/sesion';

// Con CapacitorHttp activado (capacitor.config.ts) este fetch es nativo: sin CORS ni contenido mixto.
const http: Http = (url, init) => fetch(url, init);

export const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

export const sesion = new SesionApp(http, almacenSeguro(), API_URL);
export const api = new Api(http, sesion);
export const cola = new ColaPosiciones(api);
export const rastreador = new Rastreador(
  { iniciar: iniciarRastreo, detener: detenerRastreo },
  cola,
);
