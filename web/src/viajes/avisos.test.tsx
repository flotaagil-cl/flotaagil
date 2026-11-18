/** HU-65 (CC-19, DC-62): avisos del viaje en «Tu viaje»: Web Push con un clic y la página en vivo. */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { claveComoBytes } from './push';
import { VIAJE } from './tu-viaje.test';

const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });
// Clave pública sintética de 65 bytes (punto sin comprimir), en base64url.
const CLAVE = btoa(String.fromCharCode(4, ...Array.from({ length: 64 }, (_, i) => i)))
  .replace(/\+/g, '-')
  .replace(/\//g, '_')
  .replace(/=+$/, '');
const SUSCRIPCION = { endpoint: 'https://fcm.googleapis.com/fcm/send/abc', keys: { p256dh: 'p256', auth: 'auth' } };

class SocketFalso {
  static creados: SocketFalso[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: ((evento: { code: number }) => void) | null = null;
  constructor(readonly url: string) {
    SocketFalso.creados.push(this);
  }
  close() {}
}

function montar({ clave = CLAVE as string | null, aceptaCorreo = false } = {}) {
  const servidor = new ServidorAuthFalso();
  const original = servidor.fetch;
  const llamadas: { ruta: string; cuerpo?: unknown }[] = [];
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const ruta = `${peticion.method} ${new URL(peticion.url).pathname}`;
    if (ruta.startsWith('GET /api/mi-cuenta/reservas/')) {
      llamadas.push({ ruta });
      return json(200, VIAJE);
    }
    if (ruta === 'GET /api/mi-cuenta/push/') return json(200, { clave_publica: clave });
    if (ruta === 'POST /api/mi-cuenta/push/') {
      llamadas.push({ ruta, cuerpo: await peticion.json() });
      return new Response(null, { status: 201 });
    }
    if (ruta === 'GET /api/mi-cuenta/') return json(200, { acepta_avisos_correo: aceptaCorreo });
    return original(peticion);
  };
  montarPanel(`/mis-viajes/${VIAJE.id}`, { email: 'pasajero@andes.example', servidor });
  return llamadas;
}

function navegadorConPush(permiso: NotificationPermission, pedir = vi.fn(async () => 'granted' as NotificationPermission), suscrito = false) {
  const suscribir = vi.fn(async () => ({ toJSON: () => SUSCRIPCION }));
  const pushManager = { subscribe: suscribir, getSubscription: async () => (suscrito ? { toJSON: () => SUSCRIPCION } : null) };
  const registrar = vi.fn(async () => ({ pushManager }));
  const getRegistration = vi.fn(async () => (suscrito ? { pushManager } : undefined));
  const ready = Promise.resolve({ pushManager });
  vi.stubGlobal('Notification', { permission: permiso, requestPermission: pedir });
  vi.stubGlobal('PushManager', class {});
  Object.defineProperty(navigator, 'serviceWorker', { value: { register: registrar, getRegistration, ready }, configurable: true });
  return { pedir, registrar, suscribir };
}

beforeEach(() => {
  SocketFalso.creados = [];
  vi.stubGlobal('WebSocket', SocketFalso);
});

afterEach(() => {
  Reflect.deleteProperty(navigator, 'serviceWorker');
});

describe('HU-65 · avisos del viaje', () => {
  it('activa Web Push con un clic y guarda la suscripción', async () => {
    const { pedir, registrar, suscribir } = navegadorConPush('default');
    const llamadas = montar();
    const tarjeta = (await screen.findByRole('heading', { name: 'Avisos de tu viaje' })).closest('section')!;
    await userEvent.click(await within(tarjeta).findByRole('button', { name: 'Activar avisos en este dispositivo' }));
    expect(await within(tarjeta).findByText(/Te avisaremos en este dispositivo/)).toBeInTheDocument();
    expect(pedir).toHaveBeenCalled();
    expect(registrar).toHaveBeenCalledWith('/sw-push.js');
    expect(suscribir).toHaveBeenCalledWith({ userVisibleOnly: true, applicationServerKey: claveComoBytes(CLAVE) });
    expect(llamadas).toContainEqual({ ruta: 'POST /api/mi-cuenta/push/', cuerpo: SUSCRIPCION });
    expect(within(tarjeta).getByRole('link', { name: 'Mi perfil' })).toHaveAttribute('href', '/mi-perfil');
  });

  it('si el pasajero no da permiso, no se suscribe', async () => {
    const { suscribir } = navegadorConPush('default', vi.fn(async () => 'denied' as NotificationPermission));
    montar();
    await userEvent.click(await screen.findByRole('button', { name: 'Activar avisos en este dispositivo' }));
    expect(await screen.findByText(/Los avisos están bloqueados en este navegador/)).toBeInTheDocument();
    expect(suscribir).not.toHaveBeenCalled();
  });

  it('con permiso dado pero sin suscripción en este navegador, ofrece activarlos (DC-67)', async () => {
    const { suscribir } = navegadorConPush('granted');
    const llamadas = montar();
    await userEvent.click(await screen.findByRole('button', { name: 'Activar avisos en este dispositivo' }));
    expect(await screen.findByText(/Te avisaremos en este dispositivo/)).toBeInTheDocument();
    expect(suscribir).toHaveBeenCalled();
    expect(llamadas).toContainEqual({ ruta: 'POST /api/mi-cuenta/push/', cuerpo: SUSCRIPCION });
  });

  it('con la suscripción ya hecha, los muestra activos sin botón', async () => {
    navegadorConPush('granted', undefined, true);
    montar();
    expect(await screen.findByText(/Te avisaremos en este dispositivo/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Activar avisos en este dispositivo' })).not.toBeInTheDocument();
  });

  it('sin Web Push en el servidor: solo el correo, que ya aceptó', async () => {
    navegadorConPush('default');
    montar({ clave: null, aceptaCorreo: true });
    expect(await screen.findByText(/Si no, te avisamos por correo\./)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Activar avisos en este dispositivo' })).not.toBeInTheDocument();
  });

  it('la clave VAPID pasa de base64url a bytes', () => {
    const bytes = claveComoBytes(CLAVE);
    expect([bytes.length, bytes[0], bytes[64]]).toEqual([65, 4, 63]);
  });
});

describe('HU-65 · «Tu viaje» en vivo', () => {
  it('vuelve a pedir el viaje cuando el canal avisa un cambio suyo', async () => {
    const llamadas = montar();
    await screen.findByRole('heading', { name: 'Tu viaje' });
    const canal = SocketFalso.creados.find((s) => s.url.endsWith('/ws/chat/'))!;
    const antes = llamadas.filter((l) => l.ruta.startsWith('GET /api/mi-cuenta/reservas/')).length;
    act(() => canal.onmessage!({ data: JSON.stringify({ tipo: 'viaje', viaje: 999, estado: 'CANCELADO' }) }));
    act(() => canal.onmessage!({ data: JSON.stringify({ tipo: 'viaje', viaje: VIAJE.id, estado: 'ASIGNADO' }) }));
    await waitFor(() => expect(llamadas.filter((l) => l.ruta.startsWith('GET /api/mi-cuenta/reservas/'))).toHaveLength(antes + 1));
  });
});
