/** HU-69: textos, colores y cuenta regresiva de los vuelos (antes y después de aterrizar). */

import { describe, expect, it } from 'vitest';
import type { components } from '../api/esquema';
import { formatearHora } from '../hora/hora';
import { cuentaRegresiva, duracion, estadoDeVuelo, lineaDeVuelo } from './textos';

type Viaje = components['schemas']['Viaje'];
type Vuelo = components['schemas']['Vuelo'];

// 18-11-2026 14:00 en Santiago (UTC−3).
const AHORA = Date.parse('2026-11-18T17:00:00Z');
const en = (min: number) => new Date(AHORA + min * 60_000).toISOString();

function vuelo(cambios: Partial<Vuelo> = {}): Vuelo {
  return {
    numero: 'LA845',
    fecha: '2026-11-18',
    hora_programada: en(80),
    hora_estimada: null,
    estado_vuelo: 'PROGRAMADO',
    ultima_consulta_en: en(-10),
    origen_icao: null,
    recogida_propuesta: null,
    propuesta_en: null,
    internacional: null,
    margen_min: 20,
    recogida_sugerida: en(100),
    ...cambios,
  };
}

function viaje(cambios: Partial<Viaje> = {}): Viaje {
  return {
    id: 7,
    estado: 'ASIGNADO',
    sentido: 'DESDE_AEROPUERTO',
    recogida_en: en(100),
    vuelo: vuelo(),
    vuelo_salida_en: null,
    vuelo_salida_tipo: null,
    en_aeropuerto_a_las: null,
    ...cambios,
  } as Viaje;
}

describe('duración y cuenta regresiva', () => {
  it.each([
    [45, '45 min'],
    [60, '1 h'],
    [80, '1 h 20 min'],
    [-5, '5 min'],
  ])('%i minutos → %s', (minutos, texto) => {
    expect(duracion(minutos)).toBe(texto);
  });

  it('antes de aterrizar cuenta hacia adelante y después hacia atrás', () => {
    expect(cuentaRegresiva(en(80), AHORA)).toBe('en 1 h 20 min');
    expect(cuentaRegresiva(en(0), AHORA)).toBe('ahora');
    expect(cuentaRegresiva(en(-7), AHORA)).toBe('hace 7 min');
  });
});

describe('estado del vuelo: texto y tono', () => {
  it.each<[string, Partial<Vuelo>, string, string]>([
    ['a tiempo', {}, 'a tiempo', 'ok'],
    ['demorado', { estado_vuelo: 'DEMORADO', hora_estimada: en(120) }, 'programado 15:20, demorado 40 min', 'revision'],
    ['estimada tarde sin cambiar el estado', { hora_estimada: en(95) }, 'programado 15:20, demorado 15 min', 'revision'],
    ['cancelado', { estado_vuelo: 'CANCELADO' }, 'CANCELADO por la aerolínea · revisar con el pasajero', 'peligro'],
    ['desviado', { estado_vuelo: 'DESVIADO' }, 'desviado', 'peligro'],
    ['aterrizado', { estado_vuelo: 'ATERRIZADO', hora_estimada: en(-12) }, 'aterrizó a las 13:48, hace 12 min', 'neutro'],
    ['sin verificar', { ultima_consulta_en: null }, 'sin verificar con la API de vuelos', 'neutro'],
  ])('%s', (_caso, cambios, texto, tono) => {
    expect(estadoDeVuelo(vuelo(cambios), AHORA)).toEqual({ texto, tono });
  });
});

describe('línea de vuelo del listado', () => {
  it('llegada a tiempo: vuelo, hora, cuenta regresiva y recogida (sin ciudad: no está en los datos)', () => {
    const linea = lineaDeVuelo(viaje(), AHORA)!;
    expect(linea.principal).toBe('Vuelo asociado LA845 · aterriza a las 15:20');
    expect(linea.principal).not.toContain('desde');
    expect(linea.estado).toEqual({ texto: 'a tiempo', tono: 'ok' });
    expect(linea.detalle).toEqual(['en 1 h 20 min', 'recogida 15:40']);
  });

  it('demorado con propuesta pendiente y conductor en zona', () => {
    const linea = lineaDeVuelo(
      viaje({ estado: 'EN_ZONA', vuelo: vuelo({ estado_vuelo: 'DEMORADO', hora_estimada: en(120), recogida_propuesta: en(140) }) }),
      AHORA,
    )!;
    expect(linea.principal).toBe('Vuelo asociado LA845 · aterriza a las 16:00');
    expect(linea.detalle).toEqual(['en 2 h', '⚠ propuesta de recogida 16:20 sin confirmar', 'conductor en zona']);
    expect(linea.propuesta).toBe(true);
  });

  it('aterrizado o cancelado: sin «aterriza a las» ni cuenta regresiva', () => {
    const aterrizado = lineaDeVuelo(viaje({ vuelo: vuelo({ estado_vuelo: 'ATERRIZADO', hora_estimada: en(-5) }) }), AHORA)!;
    expect(aterrizado.principal).toBe('Vuelo asociado LA845');
    expect(aterrizado.detalle).toEqual(['recogida 15:40']);
    const cancelado = lineaDeVuelo(viaje({ vuelo: vuelo({ estado_vuelo: 'CANCELADO' }) }), AHORA)!;
    expect(cancelado.estado?.tono).toBe('peligro');
  });

  it.each([
    ['NACIONAL', 'nacional', -120, '16:00'],
    ['INTERNACIONAL', 'internacional', -180, '15:00'],
  ] as const)('salida %s: despegue y hora en el aeropuerto, sin estado', (tipo, texto, antelacion, debeEstar) => {
    const despegue = en(240);
    const linea = lineaDeVuelo(
      viaje({ sentido: 'HACIA_AEROPUERTO', vuelo: null, vuelo_salida_en: despegue, vuelo_salida_tipo: tipo, en_aeropuerto_a_las: en(240 + antelacion) }),
      AHORA,
    )!;
    expect(linea.principal).toBe(`Vuelo de salida · despega a las 18:00 (${texto})`);
    expect(linea.estado).toBeNull();
    expect(linea.detalle).toEqual([`debe estar en el aeropuerto a las ${debeEstar}`]);
  });

  it('urbano: sin línea', () => {
    expect(lineaDeVuelo(viaje({ sentido: 'URBANO', vuelo: null }), AHORA)).toBeNull();
  });

  it('otro día muestra la fecha', () => {
    expect(formatearHora(en(24 * 60), AHORA)).toBe('19-11-2026 14:00');
  });
});
