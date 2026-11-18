/**
 * HU-69: textos de los vuelos para el panel. Solo usan lo que ya está en la base (el backend no consulta la API de
 * vuelos para estas pantallas). La ciudad de origen no está en VUELO, así que no se muestra ni se deduce (DC-69).
 * El color siempre acompaña a un texto: nunca es la única señal.
 */

import type { components } from '../api/esquema';
import { formatearHora } from '../hora/hora';

type Viaje = components['schemas']['Viaje'];
type Vuelo = components['schemas']['Vuelo'];

/** Colores de las insignias del sistema visual CC-20. */
export type Tono = 'ok' | 'revision' | 'peligro' | 'neutro';

export interface EstadoDeVuelo {
  texto: string;
  tono: Tono;
}

const MINUTO = 60_000;

export function llegadaDe(vuelo: Vuelo): string {
  return vuelo.hora_estimada ?? vuelo.hora_programada;
}

/** Minutos enteros de `ahora` a `iso` (negativo si ya pasó). */
export function minutosHasta(iso: string, ahora: number): number {
  return Math.round((Date.parse(iso) - ahora) / MINUTO);
}

/** «45 min», «1 h», «1 h 20 min». */
export function duracion(minutos: number): string {
  const total = Math.abs(minutos);
  const horas = Math.floor(total / 60);
  const resto = total % 60;
  if (!horas) return `${resto} min`;
  return resto ? `${horas} h ${resto} min` : `${horas} h`;
}

/** «en 1 h 20 min» antes; «hace 5 min» después. */
export function cuentaRegresiva(iso: string, ahora: number): string {
  const minutos = minutosHasta(iso, ahora);
  if (minutos > 0) return `en ${duracion(minutos)}`;
  if (minutos === 0) return 'ahora';
  return `hace ${duracion(minutos)}`;
}

export function demoraMin(vuelo: Vuelo): number {
  if (!vuelo.hora_estimada) return 0;
  return Math.max(0, minutosHasta(vuelo.hora_estimada, Date.parse(vuelo.hora_programada)));
}

/** Estado legible del vuelo de llegada, con su tono. */
export function estadoDeVuelo(vuelo: Vuelo, ahora: number): EstadoDeVuelo {
  switch (vuelo.estado_vuelo) {
    case 'CANCELADO':
      return { texto: 'CANCELADO por la aerolínea · revisar con el pasajero', tono: 'peligro' };
    case 'DESVIADO':
      return { texto: 'desviado', tono: 'peligro' };
    case 'ATERRIZADO': {
      const llegada = llegadaDe(vuelo);
      const hace = Math.max(0, -minutosHasta(llegada, ahora));
      return { texto: `aterrizó a las ${formatearHora(llegada, ahora)}, hace ${duracion(hace)}`, tono: 'neutro' };
    }
  }
  if (!vuelo.ultima_consulta_en) return { texto: 'sin verificar con la API de vuelos', tono: 'neutro' };
  const demora = demoraMin(vuelo);
  if (vuelo.estado_vuelo === 'DEMORADO' || demora > 0) {
    const programada = formatearHora(vuelo.hora_programada, ahora);
    return { texto: demora > 0 ? `programado ${programada}, demorado ${duracion(demora)}` : `demorado (programado ${programada})`, tono: 'revision' };
  }
  return { texto: 'a tiempo', tono: 'ok' };
}

/** El vuelo aún no aterriza ni se canceló o desvió: tiene sentido una cuenta regresiva. */
export function enEspera(vuelo: Vuelo): boolean {
  return vuelo.estado_vuelo === 'PROGRAMADO' || vuelo.estado_vuelo === 'DEMORADO';
}

export interface LineaDeVuelo {
  /** Primer renglón: el vuelo y su hora. */
  principal: string;
  /** Estado con su tono (solo llegadas: las salidas no se monitorean). */
  estado: EstadoDeVuelo | null;
  /** Segundo renglón: cuenta regresiva, recogida o propuesta y conductor en zona. */
  detalle: string[];
  /** Hay una propuesta de recogida sin confirmar (RN-02). */
  propuesta: boolean;
}

export function lineaDeVuelo(viaje: Viaje, ahora: number): LineaDeVuelo | null {
  const vuelo = viaje.vuelo;
  // VUELO existe solo en las llegadas (desde el aeropuerto).
  if (vuelo) {
    const estado = estadoDeVuelo(vuelo, ahora);
    const espera = enEspera(vuelo);
    const principal = espera
      ? `Vuelo asociado ${vuelo.numero} · aterriza a las ${formatearHora(llegadaDe(vuelo), ahora)}`
      : `Vuelo asociado ${vuelo.numero}`;
    const detalle: string[] = [];
    if (espera && minutosHasta(llegadaDe(vuelo), ahora) > 0) detalle.push(cuentaRegresiva(llegadaDe(vuelo), ahora));
    if (vuelo.recogida_propuesta) detalle.push(`⚠ propuesta de recogida ${formatearHora(vuelo.recogida_propuesta, ahora)} sin confirmar`);
    else detalle.push(`recogida ${formatearHora(viaje.recogida_en, ahora)}`);
    if (viaje.estado === 'EN_ZONA') detalle.push('conductor en zona');
    return { principal, estado, detalle, propuesta: Boolean(vuelo.recogida_propuesta) };
  }
  if (viaje.sentido === 'HACIA_AEROPUERTO' && viaje.vuelo_salida_en) {
    return {
      principal: `Vuelo de salida · despega a las ${formatearHora(viaje.vuelo_salida_en, ahora)}${tipoDeSalida(viaje)}`,
      estado: null,
      detalle: viaje.en_aeropuerto_a_las ? [`debe estar en el aeropuerto a las ${formatearHora(viaje.en_aeropuerto_a_las, ahora)}`] : [],
      propuesta: false,
    };
  }
  return null;
}

export function tipoDeSalida(viaje: Viaje): string {
  if (viaje.vuelo_salida_tipo === 'INTERNACIONAL') return ' (internacional)';
  if (viaje.vuelo_salida_tipo === 'NACIONAL') return ' (nacional)';
  return '';
}
