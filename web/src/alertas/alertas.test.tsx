/** HU-28: alertas visuales y sonoras en todo el panel. */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { montarPanel, esperarListado } from '../pruebas/montar';
import { viajeDePrueba, type AlertaDePrueba } from '../pruebas/servidorViajesFalso';
import { REVISION_MS } from './AlertasVuelo';
import { sonarAlerta } from './sonido';

const alerta = (id: number, cambios: Partial<AlertaDePrueba> = {}): AlertaDePrueba => ({
  id,
  viaje: 8,
  numero_vuelo: 'LA845',
  tipo: 'VUELO_CANCELADO',
  detalle: 'El vuelo LA845 fue cancelado.',
  eta: null,
  creada_en: '2026-07-15T12:00:00Z',
  atendida_en: null,
  atendida_por: null,
  ...cambios,
});

let oscilador: { frequency: { value: number }; connect: ReturnType<typeof vi.fn>; start: ReturnType<typeof vi.fn>; stop: ReturnType<typeof vi.fn> };

class AudioFalso {
  static creados = 0;
  currentTime = 0;
  destination = {};
  constructor() {
    AudioFalso.creados += 1;
  }
  createOscillator() {
    return oscilador;
  }
  createGain() {
    return { gain: { value: 0 }, connect: vi.fn() };
  }
  resume() {
    return Promise.resolve();
  }
  close() {
    return Promise.resolve();
  }
}

beforeEach(() => {
  oscilador = { frequency: { value: 0 }, connect: vi.fn(), start: vi.fn(), stop: vi.fn() };
  AudioFalso.creados = 0;
  vi.stubGlobal('AudioContext', AudioFalso);
});

afterEach(() => {
  vi.useRealTimers();
});

function preparar(alertas: AlertaDePrueba[], ruta = '/reservas') {
  const contexto = montarPanel(ruta, { email: 'despacho@andes.example' });
  contexto.viajes.alertas = alertas;
  return contexto;
}

describe('alertas de vuelos', () => {
  it('sin alertas no muestra nada', async () => {
    preparar([]);
    await esperarListado();
    expect(screen.queryByRole('region', { name: 'Alertas de vuelos' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Alertas de vuelos')).not.toBeInTheDocument();
  });

  it('muestra cada alerta en cualquier pantalla, con el enlace a su reserva', async () => {
    const contexto = preparar([
      alerta(1),
      alerta(2, { viaje: 9, tipo: 'ETA_CAMBIADA', detalle: 'El vuelo LA900 ahora llega el 15-07 10:30.' }),
      alerta(3, { viaje: 10, tipo: 'SIN_DATOS', detalle: 'La API de vuelos no entrega datos del vuelo LA901.' }),
      alerta(4, { viaje: 11, tipo: 'VUELO_DESVIADO', detalle: 'El vuelo LA902 fue desviado.' }),
    ], '/mapa');
    contexto.viajes.agregar(viajeDePrueba({ id: 8 }));
    const zona = await screen.findByLabelText('Alertas de vuelos');
    expect(within(zona).getAllByRole('listitem').map((li) => within(li).getByText(/./, { selector: 'strong' }).textContent)).toEqual([
      'Vuelo cancelado',
      'Cambió la llegada del vuelo',
      'Vuelo sin datos',
      'Vuelo desviado',
    ]);
    expect(within(zona).getByRole('link', { name: 'Ver reserva #8' })).toHaveAttribute('href', '/reservas/8');
  });

  it('marcar como atendida la quita', async () => {
    const contexto = preparar([alerta(1)]);
    await userEvent.click(await screen.findByRole('button', { name: 'Marcar como atendida la alerta de la reserva 8' }));
    await waitFor(() => expect(screen.queryByLabelText('Alertas de vuelos')).not.toBeInTheDocument());
    expect(contexto.viajes.alertas).toEqual([]);
  });

  it('si no se puede marcar lo dice y la conserva', async () => {
    const contexto = preparar([alerta(1)]);
    const boton = await screen.findByRole('button', { name: 'Marcar como atendida la alerta de la reserva 8' });
    contexto.viajes.siguiente('POST /api/alertas/1/atender/', { estado: 500, cuerpo: {} });
    await userEvent.click(boton);
    expect(await screen.findByText('No se pudo marcar la alerta. Intenta de nuevo.')).toBeInTheDocument();
    expect(screen.getByLabelText('Alertas de vuelos')).toBeInTheDocument();
  });

  it('una alerta nueva suena; las que ya estaban al abrir, no', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const contexto = preparar([alerta(1)]);
    await screen.findByLabelText('Alertas de vuelos');
    expect(AudioFalso.creados).toBe(0);
    contexto.viajes.alertas = [alerta(2, { viaje: 9 }), alerta(1)];
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REVISION_MS);
    });
    await screen.findByRole('link', { name: 'Ver reserva #9' });
    expect(AudioFalso.creados).toBe(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REVISION_MS);
    });
    expect(AudioFalso.creados).toBe(1);
  });

  it('una alerta nueva marca la reserva en el listado sin recargar', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const viaje = viajeDePrueba({ id: 8 });
    const contexto = preparar([]);
    contexto.viajes.agregar(viaje);
    await esperarListado();
    expect(screen.queryByText('Vuelo cancelado')).not.toBeInTheDocument();
    contexto.viajes.alertas = [alerta(1)];
    Object.assign(viaje, { alerta_vuelo: 'VUELO_CANCELADO' });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REVISION_MS);
    });
    const tabla = await screen.findByRole('table');
    expect(await within(tabla).findByText('Vuelo cancelado')).toBeInTheDocument();
  });

  it('la reserva afectada se marca en su ficha', async () => {
    const contexto = montarPanel('/reservas/8', { email: 'despacho@andes.example' });
    contexto.viajes.agregar(viajeDePrueba({ id: 8, alerta_vuelo: 'SIN_DATOS' }));
    const titulo = await screen.findByRole('heading', { name: /Reserva #8/ });
    expect(within(titulo).getByText('Vuelo sin datos')).toBeInTheDocument();
  });
});

describe('sonido', () => {
  it('toca dos tonos', () => {
    sonarAlerta();
    expect(oscilador.start).toHaveBeenCalledTimes(2);
    expect(oscilador.stop).toHaveBeenCalledTimes(2);
  });

  it('sin audio en el navegador no rompe', () => {
    vi.stubGlobal('AudioContext', undefined);
    expect(() => sonarAlerta()).not.toThrow();
  });

  it('si el navegador lo impide no rompe', () => {
    vi.stubGlobal('AudioContext', class { constructor() { throw new Error('bloqueado'); } });
    expect(() => sonarAlerta()).not.toThrow();
  });
});
