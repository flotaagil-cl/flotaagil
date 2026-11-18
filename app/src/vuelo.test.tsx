// @vitest-environment jsdom
/** HU-69: el vuelo en la app del conductor (estado, demora y salidas). */
import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { VueloDelViaje } from './pantallas/VueloDelViaje';
import { soloHora, textoSalida, textoVuelo, type VueloApp } from './vuelo';

// 18-11-2026 14:00 en Santiago (UTC−3).
const AHORA = Date.parse('2026-11-18T17:00:00Z');
const en = (min: number) => new Date(AHORA + min * 60_000).toISOString();
const vuelo = (cambios: Partial<VueloApp> = {}): VueloApp => ({ numero: 'LA845', hora_programada: en(60), hora_estimada: null, estado_vuelo: 'PROGRAMADO', ...cambios });

afterEach(cleanup);

describe('textoVuelo', () => {
  it.each<[string, Partial<VueloApp>, string, string, string]>([
    ['a tiempo', {}, 'Vuelo LA845 · aterriza 15:00', 'a tiempo', 'ok'],
    ['demorado 40 min', { estado_vuelo: 'DEMORADO', hora_estimada: en(100) }, 'Vuelo LA845 · aterriza 15:40', 'demorado 40 min', 'aviso'],
    ['demorado sin hora nueva', { estado_vuelo: 'DEMORADO' }, 'Vuelo LA845 · aterriza 15:00', 'demorado', 'aviso'],
    ['aterrizó', { estado_vuelo: 'ATERRIZADO', hora_estimada: en(-5) }, 'Vuelo LA845 · aterrizó 13:55', 'aterrizó hace 5 min', 'neutro'],
    ['cancelado', { estado_vuelo: 'CANCELADO' }, 'Vuelo LA845', 'cancelado por la aerolínea: consulta a la central', 'error'],
    ['desviado', { estado_vuelo: 'DESVIADO' }, 'Vuelo LA845', 'desviado: consulta a la central', 'error'],
    ['asignación sin estado', { estado_vuelo: undefined, hora_estimada: en(80) }, 'Vuelo LA845 · aterriza 15:20', 'demorado 20 min', 'aviso'],
  ])('%s', (_caso, cambios, titulo, estado, tono) => {
    expect(textoVuelo(vuelo(cambios), AHORA)).toEqual({ titulo, estado, tono });
  });

  it('salida: la hora en el aeropuerto', () => {
    expect(soloHora(en(-120))).toBe('12:00');
    expect(textoSalida(en(60))).toBe('El pasajero debe estar en el aeropuerto a las 15:00');
  });
});

describe('VueloDelViaje', () => {
  it('llegada: el estado con su color y su texto', () => {
    render(
      <dl>
        <VueloDelViaje vuelo={vuelo({ estado_vuelo: 'CANCELADO' })} />
      </dl>,
    );
    expect(screen.getByText('cancelado por la aerolínea: consulta a la central').className).toBe('estado-vuelo error');
  });

  it('salida: sin estado ni hora estimada', () => {
    render(
      <dl>
        <VueloDelViaje vuelo={null} enAeropuerto={en(60)} />
      </dl>,
    );
    expect(screen.getByText('Aeropuerto').tagName).toBe('DT');
    expect(screen.getByText('El pasajero debe estar en el aeropuerto a las 15:00').tagName).toBe('DD');
  });

  it('sin vuelo no muestra nada', () => {
    const { container } = render(
      <dl>
        <VueloDelViaje />
      </dl>,
    );
    expect(container.querySelector('dt')).toBeNull();
  });
});
