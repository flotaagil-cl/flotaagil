/** HU-38: ingresar y crear cuenta con el diseño del portal. */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { EMPRESA_PORTAL, ServidorPortalFalso } from '../pruebas/servidorPortalFalso';
import { crearRutas } from '../rutas/tabla';
import { normalizarWhatsapp } from '../portal/telefono';

const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

function montarLogin(ruta: string) {
  const servidor = new ServidorAuthFalso();
  const pedidas: string[] = [];
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const { pathname } = new URL(peticion.url);
    if (pathname.startsWith('/api/portal/')) {
      pedidas.push(pathname);
      return pathname === '/api/portal/transportes-andes/' ? json(200, EMPRESA_PORTAL) : json(404, { detail: 'No encontrado.' });
    }
    return original(peticion);
  };
  const { entorno } = crearEntorno({ servidor, locks: crearLocks() });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { pedidas, router };
}

describe('ingreso del panel (/login)', () => {
  it('marca FlotaÁgil, temporal con el administrador y aviso para pasajeros y convenios', async () => {
    const { pedidas } = montarLogin('/login');
    expect(await screen.findByRole('heading', { level: 1, name: 'Ingresar al panel' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'FlotaÁgil' })).toHaveAttribute('href', '/login');
    expect(screen.getByText(/Pídele una temporal al administrador de tu empresa/)).toBeInTheDocument();
    expect(screen.getByText(/¿Eres pasajero o empresa en convenio\? Entra desde el enlace de tu empresa/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Olvidaste/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Crear cuenta' })).not.toBeInTheDocument();
    expect(document.title).toBe('Ingresar al panel · FlotaÁgil');
    expect(pedidas).toEqual([]);
  });

  it('errores en su campo, fuera de la etiqueta', async () => {
    montarLogin('/login');
    await userEvent.click(await screen.findByRole('button', { name: 'Ingresar' }));
    expect(await screen.findByLabelText('Correo')).toHaveAccessibleDescription('Ingresa un correo válido.');
    expect(screen.getByLabelText('Contraseña')).toHaveAccessibleDescription('Ingresa tu contraseña.');
  });
});

describe('HU-38 · ingreso del portal (/solicitar/:slug/ingresar)', () => {
  it('marca de la empresa, crear cuenta, recuperar y registrar convenio', async () => {
    montarLogin('/solicitar/transportes-andes/ingresar');
    expect(await screen.findByRole('link', { name: 'Transportes Andes Demo SpA' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
    expect(screen.getByRole('heading', { level: 1, name: 'Ingresar' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Crear cuenta' })).toHaveAttribute('href', '/solicitar/transportes-andes/cuenta');
    expect(screen.getByRole('banner')).toContainElement(screen.getAllByRole('link', { name: '¿Eres empresa? Registra tu convenio' })[0]);
    expect(screen.getByRole('link', { name: '¿Olvidaste tu contraseña?' })).toHaveAttribute('href', '/recuperar');
    expect(document.title).toBe('Ingresar · Transportes Andes Demo SpA');
  });

  it('una empresa que no existe: lo explica y no ofrece crear cuenta', async () => {
    const { pedidas } = montarLogin('/solicitar/no-existe/ingresar');
    expect(await screen.findByText(/Esta empresa no tiene un portal disponible/)).toBeInTheDocument();
    expect(new Set(pedidas)).toEqual(new Set(['/api/portal/no-existe/']));
    expect(screen.getByRole('link', { name: 'FlotaÁgil' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Crear cuenta' })).not.toBeInTheDocument();
  });

  it('misma lógica de HU-33: el pasajero entra y llega a su vista', async () => {
    const { router } = montarLogin('/solicitar/transportes-andes/ingresar');
    await userEvent.type(await screen.findByLabelText('Correo'), 'pasajero@andes.example');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'clave');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/pedir'));
  });
});

function montarCrear() {
  const servidor = new ServidorPortalFalso();
  const recibidos: unknown[] = [];
  let respuesta = () => json(201, { estado: 'PENDIENTE', mensaje: 'ok' });
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    if (new URL(peticion.url).pathname === '/api/portal/transportes-andes/cuenta/') {
      recibidos.push(await peticion.json());
      return respuesta();
    }
    return original(peticion);
  };
  const { entorno } = crearEntorno({ servidor, locks: crearLocks(), ahora: servidor.ahora });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: ['/solicitar/transportes-andes/cuenta'] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { recibidos, responder: (r: () => Response) => (respuesta = r) };
}

async function completar(telefono = '9 8765 4321') {
  await userEvent.type(await screen.findByLabelText('Nombre'), 'Paula');
  await userEvent.type(screen.getByLabelText('Apellido'), 'Pasajera');
  await userEvent.type(screen.getByLabelText('Correo'), 'paula@correo.example');
  await userEvent.type(screen.getByLabelText('WhatsApp'), telefono);
  await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
  await userEvent.click(screen.getByRole('checkbox', { name: /Acepto el aviso de privacidad/ }));
}

describe('HU-38 · crear cuenta', () => {
  it('envía nombre y apellido juntos, el WhatsApp con +56 y pide confirmar', async () => {
    const { recibidos } = montarCrear();
    await completar();
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    expect(await screen.findByRole('heading', { name: 'Confirma tu cuenta' })).toBeInTheDocument();
    expect(screen.getByText(/Responde CONFIRMAR CUENTA en los próximos 15 minutos/)).toBeInTheDocument();
    expect(recibidos[0]).toEqual({
      nombre: 'Paula Pasajera',
      email: 'paula@correo.example',
      telefono: '+56987654321',
      password: 'Clave-Sintetica-2026',
      sitio_web: '',
    });
    expect(screen.getByRole('link', { name: 'Ir a ingresar' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
  });

  it('valida antes de enviar: obligatorios, mínimo de la contraseña y aviso de privacidad', async () => {
    const { recibidos } = montarCrear();
    await userEvent.type(await screen.findByLabelText('Contraseña'), 'corta');
    await userEvent.type(screen.getByLabelText('WhatsApp'), '12');
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    expect(screen.getAllByText('Completa este campo.')).toHaveLength(3);
    expect(screen.getByLabelText('Contraseña')).toHaveAccessibleDescription('Mínimo 10 caracteres.');
    expect(screen.getByLabelText('WhatsApp')).toHaveAccessibleDescription(/Revisa el número/);
    expect(screen.getByRole('checkbox')).toHaveAccessibleDescription('Para crear la cuenta debes aceptar el aviso de privacidad.');
    expect(recibidos).toEqual([]);
  });

  it('errores del servidor en su campo; 429 y otros como aviso general', async () => {
    const { responder } = montarCrear();
    responder(() => json(400, { email: ['Ese correo ya tiene una cuenta.'] }));
    await completar('+54 9 11 2345 6789');
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    expect(await screen.findByText('Ese correo ya tiene una cuenta.')).toBeInTheDocument();

    responder(() => json(400, {}));
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Revisa los datos.');

    responder(() => json(429, { detail: 'Muchas' }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos');

    responder(() => json(500, { detail: 'Error' }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo crear la cuenta');
  });

  it('la barra se oculta en el celular, el volver va a ingresar y el pie lleva el aviso de privacidad', async () => {
    montarCrear();
    await screen.findByLabelText('Nombre');
    expect(screen.getByRole('banner', { hidden: true })).toHaveAttribute('data-movil', 'oculta');
    expect(document.querySelector('a[aria-label="Volver a ingresar"]')).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
    expect(within(screen.getByRole('contentinfo')).getByRole('link', { name: 'Aviso de privacidad' })).toBeInTheDocument();
  });

  it('normalizarWhatsapp: sin + es de Chile; con + queda igual', () => {
    expect(normalizarWhatsapp('9 8765 4321')).toBe('+56987654321');
    expect(normalizarWhatsapp('09-8765-4321')).toBe('+56987654321');
    expect(normalizarWhatsapp('+54 9 11 2345 6789')).toBe('+5491123456789');
  });
});
