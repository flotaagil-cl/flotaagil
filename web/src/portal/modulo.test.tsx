/** HU-50 (CC-22, DC-51): sin el módulo de cuentas, el portal no ofrece ingreso, cuenta ni registro. CP-46. */

import { render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { crearRutas } from '../rutas/tabla';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { EMPRESA_PORTAL } from '../pruebas/servidorPortalFalso';

const json = (cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: 200, headers: { 'Content-Type': 'application/json' } });

function montar(ruta: string, modulo: boolean) {
  const servidor = new ServidorAuthFalso();
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    if (new URL(peticion.url).pathname === '/api/portal/transportes-andes/') return json({ ...EMPRESA_PORTAL, modulo_cuentas: modulo });
    return original(peticion);
  };
  // Sin sesión: el visitante del portal.
  const { entorno } = crearEntorno({ servidor, locks: crearLocks() });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { router };
}

describe('HU-50 · módulo de cuentas en el portal', () => {
  it.each(['cuenta', 'activar', 'registro-empresa'])('sin el módulo, /%s no está disponible', async (pagina) => {
    montar(`/solicitar/transportes-andes/${pagina}`, false);
    expect(await screen.findByRole('heading', { name: /no está disponible/i })).toBeInTheDocument();
  });

  it('sin el módulo, ingresar lleva al portal de la empresa', async () => {
    const { router } = montar('/solicitar/transportes-andes/ingresar', false);
    await waitFor(() => expect(router.state.location.pathname).toBe('/solicitar/transportes-andes'));
  });

  it('con el módulo, crear cuenta sigue disponible', async () => {
    montar('/solicitar/transportes-andes/cuenta', true);
    expect(await screen.findByRole('heading', { name: /crea tu cuenta/i })).toBeInTheDocument();
  });
});
