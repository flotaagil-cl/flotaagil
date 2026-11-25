/** Servicios de la app armados una sola vez: sesión, API, cola de envío y rastreador del GPS. */

import { Api } from './api';
import { API_URL } from './apiUrl';
import { CanalChat, urlDelChat } from './chat/canal';
import { CanalConductor, urlDelCanal } from './conductor/canal';
import { ColaPosiciones } from './gps/envio';
import { detenerRastreo, iniciarRastreo } from './gps/rastreo';
import { Rastreador } from './gps/turno';
import { conTiempoLimite } from './http';
import { almacenSeguro } from './sesion/almacen';
import { SesionApp, type Http } from './sesion/sesion';
import { temaApp } from './tema/instancia';

// Con CapacitorHttp activado (capacitor.config.ts) este fetch es nativo: sin CORS ni contenido mixto.
// Todas las peticiones de la app pasan por aquí: ninguna espera más de 10 s.
const http: Http = conTiempoLimite((url, init) => fetch(url, init));

export { API_URL };

export const sesion = new SesionApp(http, almacenSeguro(), API_URL);

/** CC-27 (HU-80): la paleta y el logo llegan con el usuario, al ingresar o al abrir la app. */
sesion.suscribir((estado) => {
  if (estado.fase !== 'activa' && estado.fase !== 'cambio_pendiente') return;
  void temaApp.actualizar(estado.usuario.empresa.apariencia, estado.usuario.empresa.razon_social);
});

export const api = new Api(http, sesion);
export const cola = new ColaPosiciones(api);
export const rastreador = new Rastreador(
  { iniciar: iniciarRastreo, detener: detenerRastreo },
  cola,
);

/** Viajes asignados en vivo (HU-14). */
export const canal = new CanalConductor(urlDelCanal(API_URL), sesion);

/** Chat de trabajo en vivo (CC-19). */
export const canalChat = new CanalChat(urlDelChat(API_URL), sesion);
