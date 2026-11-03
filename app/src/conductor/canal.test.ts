import { afterEach, describe, expect, it, vi } from 'vitest';
import { SinRed } from '../sesion/sesion';
import { textoDeLaNotificacion } from './alerta';
import { CanalConductor, segundosRestantes, urlDelCanal, type Asignacion, type SocketMinimo } from './canal';

class SocketFalso implements SocketMinimo {
  static creados: SocketFalso[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: ((evento: { code: number }) => void) | null = null;
  cerrado = false;
  constructor(
    readonly url: string,
    readonly protocolos: string[],
  ) {
    SocketFalso.creados.push(this);
  }
  abrir() {
    this.onopen?.();
  }
  enviar(mensaje: unknown) {
    this.onmessage?.({ data: JSON.stringify(mensaje) });
  }
  cerrar(code: number) {
    this.onclose?.({ code });
  }
  close() {
    this.cerrado = true;
  }
}

const ASIGNACION: Asignacion = {
  asignacion: 11,
  viaje: 8,
  pasajero: 'Ana Pérez',
  origen: { direccion: 'Aeropuerto SCL', lat: -33.39, lon: -70.78 },
  destino: { direccion: 'Av. Providencia 1234', lat: -33.42, lon: -70.61 },
  recogida_en: '2026-11-03T15:30:00Z',
  tarifa: 25000,
  vuelo: { numero: 'LA 845', hora_programada: '2026-11-03T15:00:00Z', hora_estimada: '2026-11-03T15:20:00Z' },
  vence_en: '2026-11-03T15:01:00Z',
};

function armar(sesion = { access: 'A1' as string | null, renovar: vi.fn(async () => 'A2' as string | null) }) {
  SocketFalso.creados = [];
  const canal = new CanalConductor('ws://api/ws/conductor/', sesion, (url, p) => new SocketFalso(url, p));
  return { canal, sesion };
}

const esperar = () => new Promise((resolver) => setTimeout(resolver, 0));

afterEach(() => {
  vi.useRealTimers();
});

describe('canal del conductor (HU-14)', () => {
  it('URL ws/wss según la API', () => {
    expect(urlDelCanal('http://10.0.2.2:8000')).toBe('ws://10.0.2.2:8000/ws/conductor/');
    expect(urlDelCanal('https://api.flotaagil.cl')).toBe('wss://api.flotaagil.cl/ws/conductor/');
  });

  it('se conecta con el access como subprotocolo y avisa una sola vez por asignación', async () => {
    const { canal } = armar();
    const avisos: number[] = [];
    canal.alRecibirAsignacion((a) => avisos.push(a.asignacion));
    canal.iniciar();
    await esperar();
    const socket = SocketFalso.creados[0];
    expect(socket.protocolos).toEqual(['flotaagil', 'A1']);
    socket.abrir();
    socket.enviar({ tipo: 'asignado', asignacion: ASIGNACION });
    socket.enviar({ tipo: 'asignado', asignacion: ASIGNACION }); // reenvío al reconectar: sin alerta repetida
    expect(avisos).toEqual([11]);
    expect(canal.estado).toEqual({ conectado: true, asignacion: ASIGNACION });
    socket.enviar({ tipo: 'sin_asignacion', asignacion: 11 });
    expect(canal.estado.asignacion).toBeNull();
  });

  it('ante 4401 renueva y se reconecta', async () => {
    const { canal, sesion } = armar();
    canal.iniciar();
    await esperar();
    SocketFalso.creados[0].cerrar(4401);
    await esperar();
    expect(sesion.renovar).toHaveBeenCalledTimes(1);
    expect(SocketFalso.creados[1].protocolos).toEqual(['flotaagil', 'A2']);
  });

  it('otros cierres: reintenta con espera creciente; detener corta todo', async () => {
    vi.useFakeTimers();
    const { canal } = armar();
    canal.iniciar();
    await vi.advanceTimersByTimeAsync(0);
    SocketFalso.creados[0].cerrar(1006);
    await vi.advanceTimersByTimeAsync(1000);
    expect(SocketFalso.creados).toHaveLength(2);
    SocketFalso.creados[1].cerrar(1006);
    await vi.advanceTimersByTimeAsync(1999);
    expect(SocketFalso.creados).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(SocketFalso.creados).toHaveLength(3);
    canal.detener();
    expect(SocketFalso.creados[2].cerrado).toBe(true);
    SocketFalso.creados[2].cerrar(1006);
    await vi.advanceTimersByTimeAsync(60_000);
    expect(SocketFalso.creados).toHaveLength(3);
  });

  it('sin red al renovar, reintenta más tarde sin cerrar la sesión', async () => {
    vi.useFakeTimers();
    const renovar = vi.fn<() => Promise<string | null>>().mockRejectedValueOnce(new SinRed()).mockResolvedValue('A3');
    const { canal } = armar({ access: null, renovar });
    canal.iniciar();
    await vi.advanceTimersByTimeAsync(0);
    expect(SocketFalso.creados).toHaveLength(0);
    await vi.advanceTimersByTimeAsync(1000);
    expect(SocketFalso.creados[0].protocolos).toEqual(['flotaagil', 'A3']);
  });

  it('cuenta regresiva y texto de la notificación', () => {
    expect(segundosRestantes('2026-11-03T15:01:00Z', Date.parse('2026-11-03T15:00:00.200Z'))).toBe(60);
    expect(segundosRestantes('2026-11-03T15:01:00Z', Date.parse('2026-11-03T15:02:00Z'))).toBe(0);
    expect(textoDeLaNotificacion(ASIGNACION)).toEqual({
      titulo: 'Nuevo viaje asignado',
      cuerpo: 'Aeropuerto SCL → Av. Providencia 1234 · vuelo LA 845. Tienes 60 s para responder.',
    });
  });
});
