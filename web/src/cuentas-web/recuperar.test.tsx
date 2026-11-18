/** HU-41: recuperar la contraseña, crear una nueva y activar la cuenta (reenviar y corregir el número). */

import { act, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter } from 'react-router';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { CONSULTA_MS } from '../portal/ActivarCuenta';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { EMPRESA_PORTAL, ServidorPortalFalso } from '../pruebas/servidorPortalFalso';
import { crearRutas } from '../rutas/tabla';

type Respuesta = { estado: number; cuerpo?: unknown } | 'red';
const json = (estado: number, cuerpo: unknown = null) =>
  new Response(cuerpo === null ? null : JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

/** Servidor público: la empresa y las respuestas programadas por ruta (en orden). */
function montar(ruta: string, programadas: Record<string, Respuesta[]> = {}) {
  const servidor = new ServidorPortalFalso();
  const recibidas: { ruta: string; cuerpo: unknown }[] = [];
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const camino = new URL(peticion.url).pathname;
    if (peticion.method === 'GET' && camino === '/api/portal/transportes-andes/') return json(200, EMPRESA_PORTAL);
    if (peticion.method === 'GET') return json(404, { detail: 'No encontrado.' });
    const cuerpo: unknown = await peticion.json().catch(() => null);
    recibidas.push({ ruta: camino, cuerpo });
    const siguiente = programadas[camino]?.shift();
    if (siguiente === 'red') throw new TypeError('Failed to fetch');
    if (siguiente) return json(siguiente.estado, siguiente.cuerpo ?? null);
    if (camino === '/api/auth/recuperar/') return json(202);
    if (camino.endsWith('/cuenta/')) return json(201, { estado: 'PENDIENTE', mensaje: 'ok' });
    if (camino.endsWith('/cuenta/estado/') || camino.endsWith('/cuenta/reenviar/')) return json(200, { activa: false, telefono: '+569******21' });
    return json(404, { detail: 'No encontrado.' });
  };
  const { entorno } = crearEntorno({ servidor, locks: crearLocks(), ahora: servidor.ahora });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { recibidas, router };
}

afterEach(() => vi.useRealTimers());

describe('HU-41 · recuperar la contraseña', () => {
  it('con la marca de la empresa: pide el enlace, «Revisa tu correo» y reenviar', async () => {
    const { recibidas } = montar('/recuperar?empresa=transportes-andes');
    expect(await screen.findByRole('heading', { name: 'Recupera tu contraseña' })).toBeInTheDocument();
    expect(await screen.findByRole('link', { name: 'Transportes Andes Demo SpA' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }));
    expect(screen.getByLabelText('Correo')).toHaveAccessibleDescription('Ingresa un correo válido.');
    await userEvent.type(screen.getByLabelText('Correo'), 'paula@correo.example');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }));
    expect(await screen.findByRole('heading', { name: 'Revisa tu correo' })).toBeInTheDocument();
    expect(screen.getByText(/Vence en 30 minutos/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Reenviar el enlace' }));
    expect(await screen.findByText('Te lo enviamos de nuevo.')).toBeInTheDocument();
    expect(recibidas.map((r) => r.ruta)).toEqual(['/api/auth/recuperar/', '/api/auth/recuperar/']);
    expect(recibidas[0].cuerpo).toEqual({ email: 'paula@correo.example' });
  });

  it('sin empresa: marca FlotaÁgil y vuelve a /login; 429 y red se explican', async () => {
    montar('/recuperar', { '/api/auth/recuperar/': [{ estado: 429 }, 'red'] });
    expect(await screen.findByRole('link', { name: 'FlotaÁgil' })).toHaveAttribute('href', '/login');
    await userEvent.type(screen.getByLabelText('Correo'), 'paula@correo.example');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo enviar');
  });

  it('nueva contraseña: reglas a la vista, valida y guarda', async () => {
    const { recibidas } = montar('/recuperar/MQ/tok-en?empresa=transportes-andes', { '/api/auth/recuperar/confirmar/': [{ estado: 204 }] });
    const nueva = await screen.findByLabelText('Nueva contraseña');
    const reglas = screen.getByRole('list', { name: 'Requisitos de la contraseña' });
    expect(within(reglas).getAllByText(/\(pendiente\)/)).toHaveLength(3);
    await userEvent.type(nueva, '1234567890');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }));
    expect(nueva).toHaveAccessibleDescription(/No puede tener solo números/);
    await userEvent.clear(nueva);
    await userEvent.type(nueva, 'Otra-Clave-Sintetica-1');
    await userEvent.type(screen.getByLabelText('Repite la contraseña'), 'Otra-Clave-Sintetica-1');
    expect(within(reglas).getAllByText(/\(cumple\)/)).toHaveLength(3);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }));
    expect(await screen.findByRole('heading', { name: 'Tu contraseña quedó lista' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
    expect(recibidas[0].cuerpo).toEqual({ uid: 'MQ', token: 'tok-en', password: 'Otra-Clave-Sintetica-1' });
  });

  it('nueva contraseña: corta, distinta, enlace vencido, rechazo del servidor y falla', async () => {
    montar('/recuperar/MQ/tok-en', {
      '/api/auth/recuperar/confirmar/': [
        { estado: 400, cuerpo: { token: ['El enlace no es válido o ya venció. Pide uno nuevo.'] } },
        { estado: 400, cuerpo: { password: ['Esta contraseña es demasiado común.'] } },
        { estado: 500 },
      ],
    });
    const nueva = await screen.findByLabelText('Nueva contraseña');
    await userEvent.type(nueva, 'corta');
    await userEvent.type(screen.getByLabelText('Repite la contraseña'), 'otra');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }));
    expect(nueva).toHaveAccessibleDescription(/Mínimo 10 caracteres/);
    expect(screen.getByLabelText('Repite la contraseña')).toHaveAccessibleDescription('Las contraseñas no coinciden.');
    await userEvent.clear(nueva);
    await userEvent.type(nueva, 'Clave-Valida-123');
    await userEvent.clear(screen.getByLabelText('Repite la contraseña'));
    await userEvent.type(screen.getByLabelText('Repite la contraseña'), 'Clave-Valida-123');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('ya venció');
    expect(screen.getByRole('link', { name: 'Pedir un enlace nuevo' })).toHaveAttribute('href', '/recuperar');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }));
    expect(await screen.findByText('Esta contraseña es demasiado común.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Guardar contraseña' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo cambiar la contraseña');
  });
});

describe('HU-41 · activa tu cuenta', () => {
  async function crearCuenta(programadas: Record<string, Respuesta[]> = {}) {
    const contexto = montar('/solicitar/transportes-andes/cuenta', programadas);
    await userEvent.type(await screen.findByLabelText('Nombre'), 'Paula');
    await userEvent.type(screen.getByLabelText('Apellido'), 'Pasajera');
    await userEvent.type(screen.getByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Teléfono'), '9 8765 4321');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
    await userEvent.click(screen.getByRole('checkbox', { name: /Acepto el aviso de privacidad/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    await screen.findByRole('heading', { name: 'Activa tu cuenta' });
    return contexto;
  }

  it('después de crearla: pasos con el correo, espera y reenviar el enlace (HU-64)', async () => {
    const { recibidas } = await crearCuenta({
      '/api/portal/transportes-andes/cuenta/reenviar/': [{ estado: 200, cuerpo: { activa: false, correo: 'p***@correo.example' } }],
    });
    const pasos = screen.getByRole('list', { name: 'Activación de tu cuenta' });
    expect(within(pasos).getAllByRole('listitem')[1]).toHaveAttribute('aria-current', 'step');
    expect(pasos).toHaveTextContent('Te lo enviamos a paula@correo.example. Vale 24 horas');
    expect(screen.getByRole('status')).toHaveTextContent('Esperando que abras el enlace…');
    await userEvent.click(screen.getByRole('button', { name: 'Reenviar el correo' }));
    expect(await screen.findByText('Te enviamos un enlace nuevo a p***@correo.example.')).toBeInTheDocument();
    const reenvios = recibidas.filter((r) => r.ruta.endsWith('/reenviar/'));
    expect(reenvios[0].cuerpo).toEqual({ email: 'paula@correo.example', password: 'Clave-Sintetica-2026' });
  });

  it('reenviar: límite, cuenta ya activa y falla', async () => {
    await crearCuenta({
      '/api/portal/transportes-andes/cuenta/reenviar/': [{ estado: 429 }, { estado: 500 }, { estado: 409, cuerpo: { code: 'cuenta_activa' } }],
    });
    const reenviar = screen.getByRole('button', { name: 'Reenviar el correo' });
    await userEvent.click(reenviar);
    expect(await screen.findByRole('alert')).toHaveTextContent('varias veces');
    await userEvent.click(reenviar);
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo reenviar');
    await userEvent.click(reenviar);
    expect(await screen.findByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
  });

  it('consulta el estado cada pocos segundos y avisa cuando se activa', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { recibidas } = await crearCuenta({
      '/api/portal/transportes-andes/cuenta/estado/': ['red', { estado: 200, cuerpo: { activa: true, correo: 'p***@correo.example' } }],
    });
    await act(async () => vi.advanceTimersByTimeAsync(CONSULTA_MS));
    await act(async () => vi.advanceTimersByTimeAsync(CONSULTA_MS));
    expect(await screen.findByText('¡Tu cuenta está activa!')).toBeInTheDocument();
    expect(recibidas.filter((r) => r.ruta.endsWith('/estado/'))).toHaveLength(2);
  });

  it('/activar: pide correo y contraseña; pendiente, activa o no encontrada', async () => {
    montar('/solicitar/transportes-andes/activar', {
      '/api/portal/transportes-andes/cuenta/estado/': [
        { estado: 400, cuerpo: { code: 'cuenta_no_encontrada' } },
        { estado: 429 },
        { estado: 200, cuerpo: { activa: false, correo: 'p***@correo.example' } },
      ],
    });
    await userEvent.type(await screen.findByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No encontramos una cuenta por activar');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByText(/Te lo enviamos a p\*{3}@correo\.example/)).toBeInTheDocument();
  });

  it('/activar con la cuenta ya activa', async () => {
    montar('/solicitar/transportes-andes/activar', {
      '/api/portal/transportes-andes/cuenta/estado/': [{ estado: 200, cuerpo: { activa: true, correo: 'p***@correo.example' } }],
    });
    await userEvent.type(await screen.findByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByText('Tu cuenta ya está activa.')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('link', { name: 'Ingresar' })).toBeInTheDocument());
  });
});

describe('HU-64 · enlace de activación (CP-56)', () => {
  const RUTA = '/api/portal/transportes-andes/cuenta/activar/';

  it('activa la cuenta una sola vez y ofrece ingresar', async () => {
    const { recibidas } = montar('/solicitar/transportes-andes/activar/token-de-prueba', {
      [RUTA]: [{ estado: 200, cuerpo: { activa: true, correo: 'p***@correo.example' } }],
    });
    expect(await screen.findByRole('heading', { name: '¡Tu cuenta está activa!' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
    expect(recibidas.filter((r) => r.ruta === RUTA)).toEqual([{ ruta: RUTA, cuerpo: { token: 'token-de-prueba' } }]);
  });

  it.each([
    ['enlace_vencido', 'El enlace venció', true],
    ['enlace_invalido', 'El enlace no es válido', false],
    ['telefono_en_uso', 'No pudimos activar tu cuenta', false],
  ])('%s: lo explica', async (codigo, titulo, ofreceOtro) => {
    montar('/solicitar/transportes-andes/activar/x', { [RUTA]: [{ estado: codigo === 'telefono_en_uso' ? 409 : 400, cuerpo: { code: codigo } }] });
    expect(await screen.findByRole('heading', { name: titulo })).toBeInTheDocument();
    const otro = screen.queryByRole('link', { name: 'Pedir un enlace nuevo' });
    if (ofreceOtro) expect(otro).toHaveAttribute('href', '/solicitar/transportes-andes/activar');
    else expect(otro).not.toBeInTheDocument();
  });
});
