// @vitest-environment jsdom
/**
 * Reproduce el fallo intermitente de HU-16 (docs/evidencias/HU-16/resultados.md): el conductor pulsa un botón, el
 * backend registra el cambio, pero una respuesta no llega. Monta la App real con la sesión, la API, el tiempo límite
 * y el canal reales; solo son falsos la red y los plugins nativos.
 */

import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ViajeActivo } from './navegacion';
import type { SocketMinimo } from './conductor/canal';

const red = vi.hoisted(() => ({
  estado: 'ACEPTADO',
  /** Rutas que no van a responder: la petición queda colgada para siempre, como en el fallo real. */
  colgar: new Map<string, number>(),
  /** Rutas cuya próxima petición no llega al servidor. */
  perder: new Set<string>(),
  /** Lecturas retenidas, para soltarlas tarde. */
  retener: false,
  retenidas: [] as (() => void)[],
  socket: null as unknown,
  llamadas: [] as string[],
}));

function viajeActivo(estado: string): ViajeActivo {
  const punto = { direccion: 'Plaza de Armas', lat: -33.43, lon: -70.65 };
  return {
    id: 8,
    estado: estado as ViajeActivo['estado'],
    pasajero: 'Ana Pérez',
    recogida_en: '2026-11-03T15:30:00Z',
    origen: punto,
    destino: punto,
    vuelo: null,
    tarifa: 12000,
    convenio: false,
    hacia: punto,
  };
}

const json = (cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: 200 });

async function httpFalso(url: string, init: RequestInit): Promise<Response> {
  const ruta = `${init.method ?? 'GET'} ${new URL(url, 'http://x.example').pathname}`;
  red.llamadas.push(ruta);
  if (red.perder.delete(ruta)) return new Promise(() => {});
  // Las acciones se aplican en el servidor aunque su respuesta no vuelva.
  if (ruta === 'POST /api/app/viajes/8/en-camino/') red.estado = 'EN_CAMINO';
  if (ruta === 'POST /api/app/viajes/8/a-bordo/') red.estado = 'PASAJERO_A_BORDO';
  const veces = red.colgar.get(ruta) ?? 0;
  if (veces > 0) {
    red.colgar.set(ruta, veces - 1);
    return new Promise(() => {});
  }
  switch (ruta) {
    case 'POST /api/auth/app/refresh/':
      return json({ access: 'A', refresh: 'R' });
    case 'GET /api/auth/yo/':
      return json({
        id: 7,
        nombre: 'Carla Conductora',
        email: 'c@andes.example',
        rol: 'CONDUCTOR',
        debe_cambiar_password: false,
        empresa: { id: 1, razon_social: 'Andes Demo', slug: 'andes' },
      });
    case 'GET /api/app/perfil/':
      return json({
        id: 3,
        nombre: 'Carla Conductora',
        estado: 'EN_VIAJE',
        vehiculo_activo: { id: 1, patente: 'ABCD12' },
        consentimiento_gps_en: '2026-11-01T12:00:00Z',
        vehiculos: [{ id: 1, patente: 'ABCD12', marca_modelo: 'Kia Rio' }],
      });
    case 'GET /api/app/viaje-activo/': {
      const foto = json({ viaje: viajeActivo(red.estado) });
      if (red.retener) {
        red.retener = false;
        await new Promise<void>((soltar) => red.retenidas.push(soltar));
      }
      return foto;
    }
    default:
      return json({ viaje: 8, estado: red.estado });
  }
}

vi.mock('./servicios', async () => {
  const { Api } = await import('./api');
  const { CanalConductor } = await import('./conductor/canal');
  const { ColaPosiciones } = await import('./gps/envio');
  const { Rastreador } = await import('./gps/turno');
  const { conTiempoLimite } = await import('./http');
  const { SesionApp } = await import('./sesion/sesion');
  const http = conTiempoLimite(httpFalso);
  const almacen = { leer: async () => 'R0', guardar: async () => {}, borrar: async () => {} };
  const sesion = new SesionApp(http, almacen, 'http://x.example');
  const api = new Api(http, sesion);
  const cola = new ColaPosiciones(api);
  const crearSocket = () => {
    const socket: SocketMinimo = { onopen: null, onmessage: null, onclose: null, close() {} };
    red.socket = socket;
    return socket;
  };
  return {
    API_URL: '',
    sesion,
    api,
    cola,
    rastreador: new Rastreador({ iniciar: async () => 'id', detener: async () => {} }, cola),
    canal: new CanalConductor('ws://x.example/ws/conductor/', sesion, crearSocket),
  };
});
vi.mock('./gps/rastreo', () => ({ abrirAjustes: async () => {}, iniciarRastreo: async () => {}, detenerRastreo: async () => {} }));
vi.mock('./conductor/alerta', () => ({ alertar: async () => {}, pedirPermisoDeNotificaciones: async () => {}, textoDeLaNotificacion: () => '' }));
vi.mock('@capacitor/app', () => ({ App: { addListener: async () => ({ remove() {} }) } }));
vi.mock('@capacitor/app-launcher', () => ({ AppLauncher: { openUrl: async () => {} } }));

async function avanzar(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function pulsar(nombre: string) {
  fireEvent.click(screen.getByRole('button', { name: nombre }));
  await avanzar(0);
}

const titulo = () => screen.getByRole('heading', { name: /Viaje en curso/ }).textContent;

function enviarAlCanal(mensaje: unknown) {
  act(() => {
    (red.socket as SocketMinimo).onmessage?.({ data: JSON.stringify(mensaje) });
  });
}

async function abrirApp() {
  const { default: App } = await import('./App');
  render(<App />);
  await avanzar(50);
  expect(titulo()).toBe('Viaje en curso · Aceptado');
  act(() => (red.socket as SocketMinimo).onopen?.());
  await avanzar(0);
}

describe('la pantalla se corrige sola cuando una respuesta no llega (HU-16)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    red.estado = 'ACEPTADO';
    red.colgar.clear();
    red.perder.clear();
    red.retener = false;
    red.retenidas.length = 0;
    red.llamadas.length = 0;
  });

  afterEach(async () => {
    const { canal, sesion } = await import('./servicios');
    canal.detener();
    cleanup();
    await sesion.logout();
    vi.useRealTimers();
  });

  it('el caso real: el backend registró el cambio, pero la lectura del viaje activo no responde', async () => {
    await abrirApp();
    red.colgar.set('GET /api/app/viaje-activo/', 1);
    await pulsar('Voy en camino');
    expect(red.estado).toBe('EN_CAMINO');

    // Durante el plazo sigue el estado anterior: es lo que vio el conductor en la prueba de HU-16.
    await avanzar(9_000);
    expect(titulo()).toBe('Viaje en curso · Aceptado');

    // Antes del tiempo límite esto se quedaba así para siempre. Ahora corta a los 10 s y reintenta a los 2 s más.
    await avanzar(3_000);
    expect(titulo()).toBe('Viaje en curso · En camino');
    expect(screen.getByRole('button', { name: 'Pasajero a bordo' })).toBeTruthy();
  });

  it('se pierde la respuesta de la acción, pero el servidor la registró: muestra el estado real, sin error', async () => {
    await abrirApp();
    red.colgar.set('POST /api/app/viajes/8/en-camino/', 1);
    await pulsar('Voy en camino');
    await avanzar(10_100);
    expect(titulo()).toBe('Viaje en curso · En camino');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('la acción no llegó al servidor: avisa, sigue en el mismo paso y se puede repetir', async () => {
    await abrirApp();
    red.perder.add('POST /api/app/viajes/8/en-camino/');
    await pulsar('Voy en camino');
    await avanzar(10_100);
    expect(screen.getByRole('alert').textContent).toContain('No se pudo conectar');
    expect(titulo()).toBe('Viaje en curso · Aceptado');
    await pulsar('Voy en camino');
    await avanzar(50);
    expect(titulo()).toBe('Viaje en curso · En camino');
  });

  it('varias lecturas seguidas colgadas: insiste hasta lograrlo', async () => {
    await abrirApp();
    red.colgar.set('GET /api/app/viaje-activo/', 3);
    await pulsar('Voy en camino');
    await avanzar(10_000 + 2_000 + 10_000 + 4_000 + 10_000);
    expect(titulo()).toBe('Viaje en curso · Aceptado');
    await avanzar(8_000 + 100);
    expect(titulo()).toBe('Viaje en curso · En camino');
  });

  it('el evento del canal en vivo corrige la pantalla sin esperar el plazo', async () => {
    await abrirApp();
    red.colgar.set('GET /api/app/viaje-activo/', 1);
    await pulsar('Voy en camino');
    await avanzar(1_000);
    expect(titulo()).toBe('Viaje en curso · Aceptado');
    enviarAlCanal({ tipo: 'viaje', viaje: 8 });
    await avanzar(50);
    expect(titulo()).toBe('Viaje en curso · En camino');
  });

  it('una lectura atrasada no vuelve la pantalla al estado anterior', async () => {
    await abrirApp();
    red.retener = true;
    enviarAlCanal({ tipo: 'viaje', viaje: 8 }); // lee ACEPTADO y se queda retenida
    await avanzar(10);
    await pulsar('Voy en camino');
    await avanzar(50);
    expect(titulo()).toBe('Viaje en curso · En camino');
    red.retenidas.forEach((soltar) => soltar());
    await avanzar(50);
    expect(titulo()).toBe('Viaje en curso · En camino');
  });

  it('después de cada acción vuelve a pedir el viaje activo', async () => {
    await abrirApp();
    red.llamadas.length = 0;
    await pulsar('Voy en camino');
    await avanzar(50);
    expect(red.llamadas).toEqual(['POST /api/app/viajes/8/en-camino/', 'GET /api/app/perfil/', 'GET /api/app/viaje-activo/']);
    red.llamadas.length = 0;
    await pulsar('Pasajero a bordo');
    await avanzar(50);
    expect(red.llamadas).toEqual(['POST /api/app/viajes/8/a-bordo/', 'GET /api/app/perfil/', 'GET /api/app/viaje-activo/']);
    expect(titulo()).toBe('Viaje en curso · Pasajero a bordo');
  });
});
