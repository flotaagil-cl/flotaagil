/**
 * Portal público (HU-19, HU-49) con el backend falso, sin sesión.
 *
 * HU-46: el formulario de invitado de HU-19 (retirado por CC-18) ya no se prueba aquí: lo usaba solo la cuenta
 * del convenio, que ahora pide con el formulario del pasajero (ver `cuentas-web/mi-convenio.test.tsx`).
 */

import { cleanup, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter, type RouteObject } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { MENSAJES } from '../api/errores';
import { crearAlmacen, crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { EMPRESA_PORTAL, ServidorPortalFalso } from '../pruebas/servidorPortalFalso';
import { crearRutas } from '../rutas/tabla';
import { esRutaDelPortal, guardarCentral, leerCentral } from '../componentes/central';

const PORTAL = '/solicitar/transportes-andes';

function montarPortal(ruta = PORTAL, servidor = new ServidorPortalFalso(), almacen = crearAlmacen(), extra: RouteObject[] = []) {
  const locks = crearLocks();
  let canales = 0;
  const { entorno } = crearEntorno({ servidor, locks, almacen, ahora: servidor.ahora });
  entorno.crearCanal = () => {
    canales++;
    return null;
  };
  const rutas = crearRutas();
  const portal = rutas.find((r) => r.path === '/solicitar/:slug')!;
  portal.children = [...(portal.children ?? []), ...extra];
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { servidor, router, locks, almacen, canales: () => canales };
}

describe('carga del portal', () => {
  it('muestra la empresa, sin sesión: ni /api/auth/, ni Web Locks, ni canal entre pestañas', async () => {
    const { servidor, locks, canales } = montarPortal();
    expect(await screen.findByRole('link', { name: 'Ingresar' })).toBeInTheDocument();
    expect(within(screen.getByRole('banner')).getByText('Transportes Andes Demo SpA')).toBeInTheDocument();
    // CC-27: además de la empresa, solo se pide su apariencia (paleta y logo).
    expect([...servidor.llamadas].sort()).toEqual(['GET /api/portal/transportes-andes/', 'GET /api/publico/apariencia/transportes-andes/']);
    expect(servidor.prohibidas).toEqual([]);
    expect(locks.solicitudes).toBe(0);
    expect(canales()).toBe(0);
  });

  it('empresa inexistente o inactiva: página clara', async () => {
    montarPortal('/solicitar/no-existe');
    expect(await screen.findByRole('heading', { name: 'Esta página de solicitudes no está disponible' })).toBeInTheDocument();
  });

  it.each([
    ['red', 'No se pudo conectar con el servidor'],
    [503, 'No se pudo conectar con el servidor'],
    [500, 'El servidor tuvo un error'],
  ] as const)('falla al cargar (%s): «%s» y Reintentar', async (falla, titulo) => {
    const servidor = new ServidorPortalFalso();
    servidor.fallaEmpresa = falla;
    montarPortal(PORTAL, servidor);
    expect(await screen.findByRole('heading', { name: titulo })).toBeInTheDocument();
    servidor.fallaEmpresa = null;
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('link', { name: 'Ingresar' })).toBeInTheDocument();
  });

  it('página de privacidad con la franja de texto provisional', async () => {
    montarPortal(`${PORTAL}/privacidad`);
    expect(await screen.findByRole('heading', { name: 'Aviso de privacidad' })).toBeInTheDocument();
    expect(screen.getByText('Texto provisional, pendiente de aprobación.')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Volver al ingreso' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
  });
});

describe('HU-49 · estados del sistema', () => {
  it('guarda los números de la central y los ofrece cuando el servidor falla', async () => {
    const servidor = new ServidorPortalFalso();
    servidor.empresas[EMPRESA_PORTAL.slug] = { ...EMPRESA_PORTAL, central: { telefono: '+56999900001', whatsapp: '+56999900001' } };
    const { almacen } = montarPortal(PORTAL, servidor);
    await screen.findByRole('link', { name: 'Ingresar' });
    expect(leerCentral(almacen, EMPRESA_PORTAL.slug)).toEqual({ telefono: '+56999900001', whatsapp: '+56999900001' });

    // Más tarde el servidor no responde: la misma empresa ofrece llamar o escribir a la central.
    cleanup();
    const caido = new ServidorPortalFalso();
    caido.fallaEmpresa = 500;
    montarPortal(PORTAL, caido, almacen);
    expect(await screen.findByRole('heading', { name: 'El servidor tuvo un error' })).toBeInTheDocument();
    const contacto = screen.getByRole('group', { name: 'Contactar a la central' });
    expect(within(contacto).getByRole('link', { name: 'Llamar a la central' })).toHaveAttribute('href', 'tel:+56999900001');
    expect(within(contacto).getByRole('link', { name: 'WhatsApp de la central' })).toHaveAttribute('href', 'https://wa.me/56999900001');
  });

  it('una pantalla del portal que falla habla de la central, no del administrador', async () => {
    const almacen = crearAlmacen();
    guardarCentral(almacen, EMPRESA_PORTAL.slug, { telefono: '+56999900001', whatsapp: '+56999900002' });
    const rota: RouteObject = {
      path: 'rota',
      lazy: async () => {
        throw new Error('Fallo cualquiera');
      },
    };
    montarPortal(`${PORTAL}/rota`, new ServidorPortalFalso(), almacen, [rota]);
    expect(await screen.findByRole('heading', { name: 'Ocurrió un error inesperado' })).toBeInTheDocument();
    expect(screen.getByText(/Si el problema sigue, contacta a la central\./)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'WhatsApp de la central' })).toHaveAttribute('href', 'https://wa.me/56999900002');
  });

  it('sin números guardados, el error no muestra botones', async () => {
    const servidor = new ServidorPortalFalso();
    servidor.fallaEmpresa = 'red';
    montarPortal(PORTAL, servidor);
    expect(await screen.findByRole('heading', { name: 'No se pudo conectar con el servidor' })).toBeInTheDocument();
    expect(screen.queryByRole('group', { name: 'Contactar a la central' })).not.toBeInTheDocument();
  });

  it('sin WhatsApp propio, el botón usa el teléfono de la central', () => {
    const almacen = crearAlmacen();
    guardarCentral(almacen, 'taxi-pacifico', { telefono: '+56999900003', whatsapp: null });
    expect(leerCentral(almacen, 'taxi-pacifico')).toEqual({ telefono: '+56999900003', whatsapp: '+56999900003' });
    expect(leerCentral(almacen)).toEqual({ telefono: '+56999900003', whatsapp: '+56999900003' });
    guardarCentral(almacen, 'taxi-pacifico', { telefono: null, whatsapp: null });
    expect(leerCentral(almacen, 'taxi-pacifico')).toBeNull();
  });

  it('solo las rutas del portal y de las cuentas web ofrecen la central', () => {
    expect(['/solicitar/x', '/pedir', '/mis-viajes/4', '/soporte', '/mi-perfil', '/mi-convenio/viajes'].every(esRutaDelPortal)).toBe(true);
    expect(['/', '/reservas', '/login', '/mi-convenios'].some(esRutaDelPortal)).toBe(false);
  });
});

describe('HU-40 · cuenta obligatoria', () => {
  it('con el módulo, la dirección del portal ofrece ingresar (y reservar sin cuenta, HU-60)', async () => {
    montarPortal(PORTAL);
    expect(await screen.findByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
  });
});

describe('fuera del portal', () => {
  it('la página no encontrada tampoco carga la sesión', async () => {
    const { servidor, locks } = montarPortal('/no/existe');
    expect(await screen.findByText('Página no encontrada')).toBeInTheDocument();
    expect(servidor.llamadas).toEqual([]);
    expect(locks.solicitudes).toBe(0);
    expect(MENSAJES.sin_conexion).toBeTruthy();
  });
});
