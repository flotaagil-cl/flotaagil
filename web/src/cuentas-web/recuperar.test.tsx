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
    await userEvent.type(screen.getByLabelText('WhatsApp'), '9 8765 4321');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
    await userEvent.click(screen.getByRole('checkbox', { name: /Acepto el aviso de privacidad/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear cuenta' }));
    await screen.findByRole('heading', { name: 'Activa tu cuenta' });
    return contexto;
  }

  it('después de crearla: pasos, espera, reenviar y corregir el número', async () => {
    const { recibidas } = await crearCuenta({
      '/api/portal/transportes-andes/cuenta/reenviar/': [
        { estado: 200, cuerpo: { activa: false, telefono: '+569******21' } },
        { estado: 400, cuerpo: { telefono: ['Número inválido.'] } },
        { estado: 200, cuerpo: { activa: false, telefono: '+569******22' } },
      ],
    });
    const pasos = screen.getByRole('list', { name: 'Activación de tu cuenta' });
    expect(within(pasos).getAllByRole('listitem')[1]).toHaveAttribute('aria-current', 'step');
    expect(screen.getByRole('status')).toHaveTextContent('Esperando tu confirmación…');
    await userEvent.click(screen.getByRole('button', { name: 'Reenviar mensaje de WhatsApp' }));
    expect(await screen.findByText('Te enviamos el mensaje de nuevo.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Corregir mi número' }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar al número nuevo' }));
    expect(screen.getByLabelText('WhatsApp correcto')).toHaveAccessibleDescription(/Revisa el número/);
    await userEvent.type(screen.getByLabelText('WhatsApp correcto'), '9 8765 4322');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar al número nuevo' }));
    expect(await screen.findByText('Número inválido.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Enviar al número nuevo' }));
    expect(await screen.findByText(/Corregimos tu número y te enviamos el mensaje al \+569\*{6}22/)).toBeInTheDocument();
    const reenvios = recibidas.filter((r) => r.ruta.endsWith('/reenviar/'));
    expect(reenvios[0].cuerpo).toEqual({ email: 'paula@correo.example', password: 'Clave-Sintetica-2026' });
    expect(reenvios[2].cuerpo).toEqual({ email: 'paula@correo.example', password: 'Clave-Sintetica-2026', telefono: '+56987654322' });
  });

  it('reenviar: límite, cuenta ya activa y falla', async () => {
    await crearCuenta({
      '/api/portal/transportes-andes/cuenta/reenviar/': [{ estado: 429 }, { estado: 500 }, { estado: 409, cuerpo: { code: 'cuenta_activa' } }],
    });
    const reenviar = screen.getByRole('button', { name: 'Reenviar mensaje de WhatsApp' });
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
      '/api/portal/transportes-andes/cuenta/estado/': ['red', { estado: 200, cuerpo: { activa: true, telefono: '+569******21' } }],
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
        { estado: 200, cuerpo: { activa: false, telefono: '+569******21' } },
      ],
    });
    await userEvent.type(await screen.findByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No encontramos una cuenta por activar');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Demasiados intentos');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByText(/Escribe CONFIRMAR CUENTA al mensaje que enviamos a \+569\*{6}21/)).toBeInTheDocument();
  });

  it('/activar con la cuenta ya activa', async () => {
    montar('/solicitar/transportes-andes/activar', {
      '/api/portal/transportes-andes/cuenta/estado/': [{ estado: 200, cuerpo: { activa: true, telefono: '+569******21' } }],
    });
    await userEvent.type(await screen.findByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Contraseña'), 'Clave-Sintetica-2026');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByText('Tu cuenta ya está activa.')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('link', { name: 'Ingresar' })).toBeInTheDocument());
  });
});
