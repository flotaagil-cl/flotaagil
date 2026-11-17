import { render } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { App } from '../App';
import { crearRutas } from '../rutas/tabla';
import { crearEntorno, crearLocks } from './entornoFalso';
import { ServidorAuthFalso } from './servidorAuthFalso';
import { EMPRESA_PORTAL } from './servidorPortalFalso';

export const jsonPortal = (estado: number, cuerpo: unknown) =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

type Responder = (peticion: Request, ruta: string) => Promise<Response | undefined> | Response | undefined;

/**
 * El portal de transportes-andes sin sesión (el visitante), con o sin el módulo de cuentas (DC-51). `responder`
 * contesta otras rutas de la API (por ejemplo, la reserva pública); lo demás va al servidor falso de sesión.
 */
export function montarPortal(ruta: string, { modulo = false, responder }: { modulo?: boolean; responder?: Responder } = {}) {
  const servidor = new ServidorAuthFalso();
  const original = servidor.fetch;
  const peticiones: { ruta: string; cuerpo: unknown }[] = [];
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const camino = `${peticion.method} ${new URL(peticion.url).pathname}`;
    if (camino === 'GET /api/portal/transportes-andes/') return jsonPortal(200, { ...EMPRESA_PORTAL, modulo_cuentas: modulo });
    if (responder && peticion.method !== 'GET') {
      peticiones.push({ ruta: camino, cuerpo: await peticion.clone().json().catch(() => null) });
    }
    const propia = responder ? await responder(peticion, camino) : undefined;
    return propia ?? original(peticion);
  };
  const { entorno } = crearEntorno({ servidor, locks: crearLocks() });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { router, peticiones };
}
