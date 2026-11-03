/** PR-07: el panel refleja el estado que el conductor cambia desde la app por el canal en vivo, sin refresco. */

import { act, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { SocketMinimo } from '../mapa/conexion';
import type { ConductorMapa } from '../mapa/estado';
import { montarPanel } from '../pruebas/montar';
import { conductorDePrueba, ServidorFlotaFalso } from '../pruebas/servidorFlotaFalso';
import { cambioEstado } from './estadoEnVivo';

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
  abrir(conductores: ConductorMapa[] = []) {
    this.onopen?.();
    this.enviar({ tipo: 'inicial', conductores });
  }
  enviar(mensaje: unknown) {
    this.onmessage?.({ data: JSON.stringify(mensaje) });
  }
  close() {
    this.cerrado = true;
  }
}

function enMapa(cambios: Partial<ConductorMapa> = {}): ConductorMapa {
  return { id: 40, nombre: 'Pedro Soto', estado: 'DISPONIBLE', patente: 'BCDF10', posicion: null, ...cambios };
}

const posicion = (segundo: number) => ({
  lat: -33.45,
  lon: -70.66,
  precision_m: 7,
  registrada_en: `2026-11-03T15:00:${String(segundo).padStart(2, '0')}Z`,
});

beforeEach(() => {
  SocketFalso.creados = [];
  vi.stubGlobal('WebSocket', SocketFalso);
});

afterEach(() => {
  vi.useRealTimers();
});

async function montar(ruta: string) {
  const contexto = montarPanel(ruta, { email: 'admin@andes.example' });
  const flota = new ServidorFlotaFalso(contexto.servidor);
  const conductor = conductorDePrueba({ id: 40, nombre: 'Pedro Soto' });
  flota.conductores.push(conductor);
  await waitFor(() => expect(SocketFalso.creados.length).toBeGreaterThan(0));
  const socket = SocketFalso.creados.at(-1)!;
  expect(socket.url).toMatch(/\/ws\/mapa\/$/);
  act(() => socket.abrir());
  return { ...contexto, conductor, socket };
}

const pedidas = (urls: string[]) => urls.filter((u) => u.startsWith('GET /api/conductores/')).length;

describe('cambioEstado', () => {
  it('cuenta el turno, el estado y el vehículo; no las posiciones', () => {
    const antes = new Map([[40, enMapa({ posicion: posicion(1) })]]);
    expect(cambioEstado(antes, new Map([[40, enMapa({ posicion: posicion(2) })]]))).toBe(false);
    expect(cambioEstado(antes, new Map([[40, enMapa({ estado: 'EN_VIAJE' })]]))).toBe(true);
    expect(cambioEstado(antes, new Map([[40, enMapa({ patente: 'GHJK20' })]]))).toBe(true);
    expect(cambioEstado(antes, new Map())).toBe(true);
    expect(cambioEstado(antes, new Map([[41, enMapa({ id: 41 })]]))).toBe(true);
  });
});

describe('estado en vivo en Conductores', () => {
  it('el listado cambia al instante cuando el conductor empieza y termina su turno', async () => {
    const { conductor, socket } = await montar('/conductores');
    await screen.findByRole('columnheader', { name: 'Nombre' });
    expect(within(screen.getByRole('table')).getByText('No disponible')).toBeInTheDocument();

    Object.assign(conductor, { estado: 'DISPONIBLE', vehiculo_activo: { id: 1, patente: 'BCDF10' } });
    act(() => socket.enviar({ tipo: 'conductor', conductor: enMapa() }));
    expect(await within(screen.getByRole('table')).findByText('Disponible')).toBeInTheDocument();

    Object.assign(conductor, { estado: 'NO_DISPONIBLE', vehiculo_activo: null });
    act(() => socket.enviar({ tipo: 'fuera', id: 40 }));
    expect(await within(screen.getByRole('table')).findByText('No disponible')).toBeInTheDocument();
  });

  it('la ficha también se actualiza', async () => {
    const { conductor, socket } = await montar('/conductores/40');
    await screen.findByRole('heading', { name: 'Pedro Soto' });
    Object.assign(conductor, { estado: 'DISPONIBLE', vehiculo_activo: { id: 1, patente: 'BCDF10' } });
    act(() => socket.enviar({ tipo: 'conductor', conductor: enMapa() }));
    expect(await screen.findByText(/Disponible · declaró BCDF10/)).toBeInTheDocument();
  });

  it('una posición nueva no vuelve a pedir los datos', async () => {
    const { socket, servidor } = await montar('/conductores');
    await screen.findByRole('columnheader', { name: 'Nombre' });
    act(() => socket.enviar({ tipo: 'conductor', conductor: enMapa({ posicion: posicion(1) }) }));
    await waitFor(() => expect(within(screen.getByRole('table')).getByText('Pedro Soto')).toBeInTheDocument());
    await waitFor(() => expect(screen.queryByText('Actualizando…')).not.toBeInTheDocument());
    const antes = pedidas(servidor.urls);
    act(() => socket.enviar({ tipo: 'conductor', conductor: enMapa({ posicion: posicion(2) }) }));
    act(() => socket.enviar({ tipo: 'conductor', conductor: enMapa({ posicion: posicion(3) }) }));
    await act(async () => {
      await new Promise((resolver) => setTimeout(resolver, 50));
    });
    expect(pedidas(servidor.urls)).toBe(antes);
  });

  it('ya no hay refresco por tiempo: sin avisos no se vuelve a pedir nada', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { servidor } = await montar('/conductores');
    await screen.findByRole('columnheader', { name: 'Nombre' });
    await waitFor(() => expect(screen.queryByText('Actualizando…')).not.toBeInTheDocument());
    const antes = pedidas(servidor.urls);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(25_000);
    });
    expect(pedidas(servidor.urls)).toBe(antes);
  });

  it('si la conexión se corta lo avisa, y al volver recupera el cambio perdido', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { conductor, socket } = await montar('/conductores');
    await screen.findByRole('columnheader', { name: 'Nombre' });
    act(() => socket.onclose?.({ code: 1006 }));
    expect(await screen.findByText('Sin conexión en vivo: el estado puede estar desactualizado. Reconectando…')).toBeInTheDocument();

    Object.assign(conductor, { estado: 'DISPONIBLE', vehiculo_activo: { id: 1, patente: 'BCDF10' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    await waitFor(() => expect(SocketFalso.creados.at(-1)).not.toBe(socket));
    act(() => SocketFalso.creados.at(-1)!.abrir([enMapa()]));
    expect(await within(screen.getByRole('table')).findByText('Disponible')).toBeInTheDocument();
    expect(screen.queryByText(/Sin conexión en vivo/)).not.toBeInTheDocument();
  });

  it('al salir de la pantalla cierra la conexión', async () => {
    const { socket, router } = await montar('/conductores');
    await screen.findByRole('columnheader', { name: 'Nombre' });
    await act(async () => {
      await router.navigate('/');
    });
    await waitFor(() => expect(socket.cerrado).toBe(true));
  });
});
