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
import type { VueloApp } from './vuelo';

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
  /** CC-19: socket del chat y pitidos de mensajes. */
  chat: null as unknown,
  sonidos: 0,
  /** Lugar en la fila que devuelve el perfil. */
  fila: null as unknown,
  llamadas: [] as string[],
  // HU-69: vuelo de llegada del viaje activo (null: sin vuelo).
  vuelo: null as VueloApp | null,
  /** Listener del botón Atrás de Android y conteo de minimizaciones. */
  atras: null as (() => void) | null,
  minimizaciones: 0,
  /** Asignación pendiente devuelta por GET /api/app/perfil/ (fallback HTTP / pull-to-refresh). */
  asignacionPendiente: null as unknown,
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
    vuelo: red.vuelo?.numero ?? null,
    detalle_vuelo: red.vuelo,
    tarifa: 12000,
    convenio: false,
    hacia: punto,
    navegar_con: 'COORDENADAS',
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
        fila: red.fila,
        asignacion_pendiente: red.asignacionPendiente,
      });
    case 'GET /api/app/viaje-activo/': {
      const foto = json({ viaje: viajeActivo(red.estado) });
      if (red.retener) {
        red.retener = false;
        await new Promise<void>((soltar) => red.retenidas.push(soltar));
      }
      return foto;
    }
    case 'GET /api/chat/conversaciones/':
      return json([{ id: 1, tipo: 'CENTRAL', titulo: 'Central', no_leidos: 2, ultimo: null }]);
    case 'GET /api/chat/conversaciones/1/mensajes/':
      return json({ results: [], hay_mas: false, leido_por_otros_hasta: 0 });
    case 'GET /api/chat/personal/':
      return json([{ id: 2, nombre: 'Ana Rojas' }]);
    case 'GET /api/app/mi-turno/':
      return json({ en_turno: true, inicio: '2026-11-04T12:00:00Z', fin: null, viajes: [], totales: [], total: 0 });
    default:
      return json({ viaje: 8, estado: red.estado });
  }
}

vi.mock('./servicios', async () => {
  const { Api } = await import('./api');
  const { CanalConductor } = await import('./conductor/canal');
  const { CanalChat } = await import('./chat/canal');
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
    // CC-19: el canal del chat con su propio socket falso.
    canalChat: new CanalChat('ws://x.example/ws/chat/', sesion, () => {
      const socket: SocketMinimo = { onopen: null, onmessage: null, onclose: null, close() {} };
      red.chat = socket;
      return socket;
    }),
  };
});
vi.mock('./gps/rastreo', () => ({ abrirAjustes: async () => {}, iniciarRastreo: async () => {}, detenerRastreo: async () => {} }));
vi.mock('./conductor/alerta', () => ({
  alertar: async () => {},
  pedirPermisoDeNotificaciones: async () => {},
  textoDeLaNotificacion: () => '',
  sonarMensaje: () => {
    red.sonidos += 1;
  },
}));
vi.mock('@capacitor/app', () => ({
  App: {
    addListener: async (evento: string, fn: () => void) => {
      if (evento === 'backButton') red.atras = fn;
      return {
        remove() {
          if (evento === 'backButton' && red.atras === fn) red.atras = null;
        },
      };
    },
    minimizeApp: async () => {
      red.minimizaciones += 1;
    },
  },
}));
vi.mock('@capacitor/app-launcher', () => ({ AppLauncher: { openUrl: async () => {} } }));

async function avanzar(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

async function pulsar(nombre: string | RegExp) {
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
    red.fila = null;
    red.perder.clear();
    red.retener = false;
    red.retenidas.length = 0;
    red.llamadas.length = 0;
    red.vuelo = null;
    red.atras = null;
    red.minimizaciones = 0;
    red.asignacionPendiente = null;
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

  it('muestra el lugar en la fila y lo actualiza con el evento del canal (HU-29)', async () => {
    red.fila = { posicion: 2, total: 3, zona: 'Aeropuerto SCL', ingreso_en: '2026-11-03T15:00:00Z' };
    await abrirApp();
    expect(screen.getByRole('status').textContent).toContain('Vas en el lugar 2 de 3 · Aeropuerto SCL');
    red.fila = { posicion: 1, total: 2, zona: 'Aeropuerto SCL', ingreso_en: '2026-11-03T15:00:00Z' };
    enviarAlCanal({ tipo: 'fila' });
    await avanzar(50);
    expect(screen.getByRole('status').textContent).toContain('Eres el primero de 2');
    red.fila = null;
    enviarAlCanal({ tipo: 'fila' });
    await avanzar(50);
    expect(screen.queryByRole('status')).toBeNull();
  });

  it('HU-69: con un vuelo de llegada relee el viaje cada minuto y muestra la demora', async () => {
    const llegada = new Date(Date.now() + 60 * 60_000).toISOString();
    red.vuelo = { numero: 'LA845', hora_programada: llegada, hora_estimada: null, estado_vuelo: 'PROGRAMADO' };
    await abrirApp();
    expect(screen.getByText('a tiempo').className).toBe('estado-vuelo ok');
    red.vuelo = { ...red.vuelo, estado_vuelo: 'DEMORADO', hora_estimada: new Date(Date.parse(llegada) + 40 * 60_000).toISOString() };
    await avanzar(60_000);
    expect(screen.getByText('demorado 40 min').className).toBe('estado-vuelo aviso');
  });

  it('sin vuelo no relee el viaje por su cuenta', async () => {
    await abrirApp();
    red.llamadas.length = 0;
    await avanzar(60_000);
    expect(red.llamadas.filter((l) => l === 'GET /api/app/viaje-activo/')).toEqual([]);
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

  it('un mensaje del chat suena, avisa en el inicio y abre el chat con el aviso de manejo (HU-63)', async () => {
    red.sonidos = 0;
    await abrirApp();
    expect(screen.getByRole('button', { name: 'Chat (2 sin leer)' })).toBeTruthy();
    const mensaje = { id: 5, conversacion: 1, texto: 'Te espera en la puerta 3', rapida: '', autor: 'Central', propio: false, creado_en: '2026-11-17T12:00:00Z' };
    act(() => (red.chat as SocketMinimo).onmessage?.({ data: JSON.stringify({ tipo: 'mensaje', mensaje: { ...mensaje, id: 6, propio: true } }) }));
    act(() => (red.chat as SocketMinimo).onmessage?.({ data: JSON.stringify({ tipo: 'mensaje', mensaje }) }));
    await avanzar(50);
    expect(red.sonidos).toBe(1);
    expect(screen.getByText('Nuevo mensaje de Central: Te espera en la puerta 3')).toBeTruthy();
    await pulsar('Abrir chat');
    await avanzar(50);
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeTruthy();
    expect(screen.getByRole('status').textContent).toContain('Evita escribir mientras manejas');
    await pulsar('Volver al inicio');
    expect(screen.queryByText(/Nuevo mensaje de Central/)).toBeNull();
  });

  it('muestra la asignación como tarjeta prioritaria en Inicio, compacta Turno/Ubicación y acepta el viaje', async () => {
    await abrirApp();
    expect(screen.queryByRole('button', { name: 'Actualizar' })).toBeNull();
    expect(document.querySelectorAll('.tarjeta.compacta')).toHaveLength(2);
    expect(document.querySelector('.tarjeta.viaje.prioritaria')).toBeTruthy();

    const vence = new Date(Date.now() + 60_000).toISOString();
    enviarAlCanal({
      tipo: 'asignado',
      asignacion: {
        asignacion: 42,
        viaje: 99,
        pasajero: 'Luis Soto',
        origen: { direccion: 'Aeropuerto SCL', lat: -33.39, lon: -70.79 },
        destino: { direccion: 'Las Condes 400', lat: -33.41, lon: -70.57 },
        recogida_en: '2026-11-03T16:00:00Z',
        tarifa: 25000,
        vuelo: null,
        vence_en: vence,
      },
    });
    await avanzar(50);
    expect(screen.getByRole('heading', { name: 'Hola, Carla Conductora' })).toBeTruthy();
    expect(screen.getByRole('heading', { name: 'Nuevo viaje asignado' })).toBeTruthy();
    expect(screen.getByText('Luis Soto')).toBeTruthy();

    red.llamadas.length = 0;
    await pulsar('Aceptar viaje');
    await avanzar(50);
    expect(red.llamadas).toContain('POST /api/app/asignaciones/42/aceptar/');
  });

  it('pull-to-refresh en Inicio recarga perfil, viaje activo y chats', async () => {
    await abrirApp();
    red.llamadas.length = 0;
    const zona = document.querySelector('.tirar')!;
    fireEvent.touchStart(zona, { touches: [{ clientY: 0 }] });
    fireEvent.touchMove(zona, { touches: [{ clientY: 160 }] });
    fireEvent.touchEnd(zona);
    await avanzar(50);
    expect(red.llamadas).toContain('GET /api/app/perfil/');
    expect(red.llamadas).toContain('GET /api/app/viaje-activo/');
    expect(red.llamadas).toContain('GET /api/chat/conversaciones/');
  });

  it('el botón Atrás de Android navega hacia atrás en subpantallas y minimiza solo desde Inicio', async () => {
    await abrirApp();
    const presionarAtras = async () => {
      act(() => red.atras?.());
      await avanzar(50);
    };

    // Mi turno → Inicio
    await pulsar('Mi turno');
    expect(screen.getByRole('heading', { name: 'Mi turno' })).toBeTruthy();
    await presionarAtras();
    expect(screen.getByRole('heading', { name: 'Hola, Carla Conductora' })).toBeTruthy();
    expect(red.minimizaciones).toBe(0);

    // Chat → Hilo → Lista → Nuevo directo → Lista → Nuevo grupo → Lista → Inicio
    await pulsar('Chat (2 sin leer)');
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeTruthy();
    await pulsar(/Central/);
    expect(screen.getByRole('heading', { name: 'Central' })).toBeTruthy();
    await presionarAtras();
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeTruthy();

    await pulsar('Nuevo directo');
    expect(screen.getByRole('heading', { name: 'Nuevo directo' })).toBeTruthy();
    await presionarAtras();
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeTruthy();

    await pulsar('Nuevo grupo');
    expect(screen.getByRole('heading', { name: 'Nuevo grupo' })).toBeTruthy();
    await presionarAtras();
    expect(screen.getByRole('heading', { name: 'Chat' })).toBeTruthy();

    await presionarAtras();
    expect(screen.getByRole('heading', { name: 'Hola, Carla Conductora' })).toBeTruthy();
    expect(red.minimizaciones).toBe(0);

    // Ya en Inicio → minimiza la app
    await presionarAtras();
    expect(red.minimizaciones).toBe(1);
  });

  it('pull-to-refresh muestra la asignación pendiente devuelta por perfil aunque no llegue por WebSocket', async () => {
    await abrirApp();
    expect(screen.queryByRole('heading', { name: 'Nuevo viaje asignado' })).toBeNull();

    red.asignacionPendiente = {
      asignacion: 77,
      viaje: 88,
      pasajero: 'Pedro Díaz',
      origen: { direccion: 'Costanera Center', lat: -33.41, lon: -70.6 },
      destino: { direccion: 'Aeropuerto SCL', lat: -33.39, lon: -70.79 },
      recogida_en: '2026-11-03T17:00:00Z',
      tarifa: 18000,
      vuelo: null,
      vence_en: new Date(Date.now() + 60_000).toISOString(),
    };

    const zona = document.querySelector('.tirar')!;
    fireEvent.touchStart(zona, { touches: [{ clientY: 0 }] });
    fireEvent.touchMove(zona, { touches: [{ clientY: 160 }] });
    fireEvent.touchEnd(zona);
    await avanzar(50);

    expect(screen.getByRole('heading', { name: 'Nuevo viaje asignado' })).toBeTruthy();
    expect(screen.getByText('Pedro Díaz')).toBeTruthy();
  });
});
