/** HU-02: mapa en tiempo real (estado, conexión WebSocket y pantalla). */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ConexionMapa, urlDelMapa, type SocketMinimo } from './conexion';
import { aplicar, confianza, encuadre, type ConductorMapa } from './estado';

const AHORA = Date.parse('2026-11-03T15:00:00Z');

function conductor(cambios: Partial<ConductorMapa> = {}): ConductorMapa {
  return {
    id: 1,
    nombre: 'Pedro Soto',
    estado: 'DISPONIBLE',
    patente: 'BCDF10',
    posicion: { lat: -33.45, lon: -70.66, precision_m: 8, registrada_en: new Date(AHORA - 5000).toISOString() },
    ...cambios,
  };
}

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
  abrir(mensaje?: unknown) {
    this.onopen?.();
    if (mensaje) this.enviar(mensaje);
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

beforeEach(() => {
  SocketFalso.creados = [];
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('estado del mapa', () => {
  it('posición confiable, antigua (> 60 s), imprecisa o sin posición', () => {
    expect(confianza(conductor(), AHORA)).toEqual({ confiable: true });
    const vieja = conductor({ posicion: { ...conductor().posicion!, registrada_en: new Date(AHORA - 61_000).toISOString() } });
    expect(confianza(vieja, AHORA)).toEqual({ confiable: false, motivo: 'antigua' });
    expect(confianza(conductor({ posicion: { ...conductor().posicion!, precision_m: 150 } }), AHORA)).toEqual({ confiable: false, motivo: 'imprecisa' });
    expect(confianza(conductor({ posicion: null }), AHORA)).toEqual({ confiable: false, motivo: 'sin_posicion' });
  });

  it('aplica inicial, cambios y salidas; un aviso tardío no retrocede la posición', () => {
    let mapa = aplicar(new Map(), { tipo: 'inicial', conductores: [conductor(), conductor({ id: 2, nombre: 'Ana' })] });
    expect([...mapa.keys()]).toEqual([1, 2]);
    const nueva = { ...conductor().posicion!, lat: -33.4, registrada_en: new Date(AHORA).toISOString() };
    mapa = aplicar(mapa, { tipo: 'conductor', conductor: conductor({ posicion: nueva }) });
    mapa = aplicar(mapa, { tipo: 'conductor', conductor: conductor({ estado: 'EN_VIAJE' }) }); // posición más vieja
    expect(mapa.get(1)).toMatchObject({ estado: 'EN_VIAJE', posicion: { lat: -33.4 } });
    mapa = aplicar(mapa, { tipo: 'fuera', id: 2 });
    expect([...mapa.keys()]).toEqual([1]);
  });

  it('encuadre por defecto en Santiago y con margen alrededor de las posiciones', () => {
    expect(encuadre([])).toMatchObject({ latMin: -33.55, lonMax: -70.55 });
    const zona = encuadre([conductor()]);
    expect(zona.latMin).toBeLessThan(-33.45);
    expect(zona.latMax).toBeGreaterThan(-33.45);
  });
});

describe('conexión', () => {
  function armar(access: string | null = 'A1', renovado: string | null = 'A2') {
    const sesion = { access: vi.fn(() => access), renovarTrasRechazo: vi.fn(async () => renovado) };
    const conexion = new ConexionMapa('ws://panel/ws/mapa/', sesion, (url, p) => new SocketFalso(url, p), () => AHORA);
    return { sesion, conexion };
  }

  it('usa wss con https y el access como subprotocolo', () => {
    expect(urlDelMapa('https://panel.flotaagil.cl')).toBe('wss://panel.flotaagil.cl/ws/mapa/');
    const { conexion } = armar();
    conexion.iniciar();
    return waitFor(() => expect(SocketFalso.creados[0]?.protocolos).toEqual(['flotaagil', 'A1']));
  });

  it('ante 4401 renueva el access y se reconecta', async () => {
    const { conexion, sesion } = armar();
    conexion.iniciar();
    await waitFor(() => expect(SocketFalso.creados).toHaveLength(1));
    SocketFalso.creados[0].abrir({ tipo: 'inicial', conductores: [conductor()] });
    expect(conexion.estado.fase).toBe('conectado');
    SocketFalso.creados[0].cerrar(4401);
    await waitFor(() => expect(SocketFalso.creados).toHaveLength(2));
    expect(sesion.renovarTrasRechazo).toHaveBeenCalledTimes(1);
    expect(SocketFalso.creados[1].protocolos).toEqual(['flotaagil', 'A2']);
  });

  it('si la sesión terminó queda sin_sesion', async () => {
    const { conexion } = armar('A1', null);
    conexion.iniciar();
    await waitFor(() => expect(SocketFalso.creados).toHaveLength(1));
    SocketFalso.creados[0].cerrar(4401);
    await waitFor(() => expect(conexion.estado.fase).toBe('sin_sesion'));
  });

  it('otros cierres: reconecta con espera creciente', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { conexion } = armar();
    conexion.iniciar();
    await waitFor(() => expect(SocketFalso.creados).toHaveLength(1));
    SocketFalso.creados[0].cerrar(1006);
    expect(conexion.estado.fase).toBe('reconectando');
    await vi.advanceTimersByTimeAsync(1000);
    expect(SocketFalso.creados).toHaveLength(2);
    SocketFalso.creados[1].cerrar(1006);
    await vi.advanceTimersByTimeAsync(1000);
    expect(SocketFalso.creados).toHaveLength(2); // ahora espera 2 s
    await vi.advanceTimersByTimeAsync(1000);
    expect(SocketFalso.creados).toHaveLength(3);
    conexion.detener();
    expect(SocketFalso.creados[2].cerrado).toBe(true);
  });
});

describe('pantalla del mapa', () => {
  it('muestra los conductores en turno, la ficha al seleccionar y marca la posición antigua', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true, now: AHORA });
    vi.stubGlobal('WebSocket', SocketFalso);
    montarPanel('/mapa', { email: 'despacho@andes.example' });
    await screen.findByRole('heading', { name: 'Mapa', level: 1 });
    await waitFor(() => expect(SocketFalso.creados).toHaveLength(1));
    expect(SocketFalso.creados[0].url).toMatch(/\/ws\/mapa\/$/);
    act(() => SocketFalso.creados[0].abrir({ tipo: 'inicial', conductores: [conductor(), conductor({ id: 2, nombre: 'Ana Ríos', patente: 'GHJK20', estado: 'EN_VIAJE' })] }));

    expect(await screen.findByText('En vivo · 2 conductores en turno')).toBeInTheDocument();
    const lista = screen.getByRole('list', { name: 'Conductores en turno' });
    expect(within(lista).getAllByRole('button').map((b) => b.textContent)).toEqual([
      expect.stringContaining('Ana Ríos'),
      expect.stringContaining('Pedro Soto'),
    ]);
    await userEvent.click(within(lista).getByRole('button', { name: /Pedro Soto/ }));
    const ficha = screen.getByRole('region', { name: 'Conductor seleccionado' });
    expect(within(ficha).getByText('BCDF10')).toBeInTheDocument();
    expect(within(ficha).getByText('Disponible')).toBeInTheDocument();
    expect(within(ficha).queryByText(/no confiable/)).not.toBeInTheDocument();

    // Pasan 60 s sin posiciones nuevas: queda marcada como no confiable.
    await act(async () => {
      await vi.advanceTimersByTimeAsync(60_000);
    });
    expect(within(ficha).getByText('Posición de hace más de 60 s: no confiable')).toBeInTheDocument();

    // Llega una posición nueva y sale Ana del turno.
    act(() => {
      SocketFalso.creados[0].enviar({ tipo: 'conductor', conductor: conductor({ posicion: { ...conductor().posicion!, registrada_en: new Date(Date.now()).toISOString() } }) });
      SocketFalso.creados[0].enviar({ tipo: 'fuera', id: 2 });
    });
    await waitFor(() => expect(within(ficha).queryByText(/no confiable/)).not.toBeInTheDocument());
    expect(screen.getByText('En vivo · 1 conductor en turno')).toBeInTheDocument();
  });

  it('el menú muestra Mapa al despachador', async () => {
    vi.stubGlobal('WebSocket', SocketFalso);
    montarPanel('/', { email: 'despacho@andes.example' });
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Mapa' })).toHaveAttribute('href', '/mapa');
  });

  it('sin conexión avisa que reintenta', async () => {
    vi.stubGlobal('WebSocket', SocketFalso);
    montarPanel('/mapa', { email: 'despacho@andes.example' });
    await waitFor(() => expect(SocketFalso.creados).toHaveLength(1));
    act(() => SocketFalso.creados[0].cerrar(1006));
    expect(await screen.findByText('Se perdió la conexión en vivo. Reintentando…')).toBeInTheDocument();
  });
});
