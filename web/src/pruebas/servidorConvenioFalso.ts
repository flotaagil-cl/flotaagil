/**
 * Backend falso del link del convenio (HU-25). La sesión la lleva una cookie httpOnly en el backend real: aquí es
 * un booleano. Cualquier llamada a /api/auth/ queda en `prohibidas`: este acceso no usa la sesión del panel.
 */

import type { AccesoConvenio, SolicitudConvenio } from '../portal/api';
import { AHORA_PORTAL, EMPRESA_PORTAL } from './servidorPortalFalso';

export const TOKEN = 'tokenSintetico'.padEnd(43, 'x');
const CLAVE = 'ClaveSintetica23';

function json(estado: number, cuerpo?: unknown): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });
}

export class ServidorConvenioFalso {
  sesion = false;
  activo = true;
  bloqueado = false;
  intentos = 0;
  cuerpos: SolicitudConvenio[] = [];
  prohibidas: string[] = [];
  /** El próximo POST de solicitud responde que la sesión venció. */
  vencerSesion = false;
  /** Desactivan el convenio con la sesión abierta. */
  desactivarAlEnviar = false;
  fallaAcceso: 'red' | null = null;
  /** El próximo POST de solicitud responde 400 con estos campos. */
  errorDeCampo: Record<string, string[]> | null = null;

  constructor(readonly ahora = AHORA_PORTAL) {}

  fetch = async (entrada: Request | string, init?: RequestInit): Promise<Response> => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const { pathname } = new URL(peticion.url);
    if (!pathname.startsWith(`/api/convenio/${TOKEN}/`)) {
      if (pathname.startsWith('/api/auth/')) this.prohibidas.push(pathname);
      return json(404, { detail: 'No encontrado.' });
    }
    if (!this.activo) return json(404, { detail: 'No encontrado.' });
    const recurso = pathname.split('/')[4];
    if (peticion.method === 'GET') {
      if (this.fallaAcceso === 'red') throw new TypeError('Failed to fetch');
      const acceso: AccesoConvenio = {
        ...EMPRESA_PORTAL,
        sesion_activa: this.sesion,
        cliente_nombre: this.sesion ? 'Minera Sintética S.A.' : null,
      };
      return json(200, acceso);
    }
    if (recurso === 'sesion') {
      if (this.bloqueado) return json(423, { detail: 'Bloqueado.', code: 'convenio_bloqueado' });
      const { password } = (await peticion.json()) as { password: string };
      if (password !== CLAVE) {
        this.intentos += 1;
        if (this.intentos >= 5) {
          this.bloqueado = true;
          return json(423, { detail: 'Bloqueado.', code: 'convenio_bloqueado' });
        }
        return json(401, { detail: 'Mala.', code: 'credenciales_invalidas' });
      }
      this.sesion = true;
      return json(200, { cliente_nombre: 'Minera Sintética S.A.' });
    }
    if (recurso === 'salir') {
      this.sesion = false;
      return json(204);
    }
    if (this.desactivarAlEnviar) {
      this.activo = false;
      return json(404, { detail: 'No encontrado.' });
    }
    if (this.vencerSesion) {
      this.sesion = false;
      return json(401, { detail: 'Vencida.', code: 'sesion_convenio_vencida' });
    }
    if (this.errorDeCampo) return json(400, this.errorDeCampo);
    const cuerpo = (await peticion.json()) as SolicitudConvenio;
    this.cuerpos.push(cuerpo);
    return json(201, { estado: 'SOLICITADO', recogida_en: cuerpo.recogida_en, mensaje: 'Recibimos la solicitud.' });
  };
}
