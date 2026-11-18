/**
 * HU-69: el vuelo en la app del conductor. Llegadas: «Vuelo LA845 · aterriza 15:20» con el estado o la demora;
 * salidas: la hora a la que el pasajero debe estar en el aeropuerto. El backend solo lee la base.
 */

export interface VueloApp {
  numero: string;
  hora_programada: string;
  hora_estimada: string | null;
  /** PROGRAMADO, DEMORADO, ATERRIZADO, CANCELADO o DESVIADO. Las asignaciones antiguas pueden no traerlo. */
  estado_vuelo?: string;
}

export type TonoVuelo = 'ok' | 'aviso' | 'error' | 'neutro';

const HORA = new Intl.DateTimeFormat('es-CL', { timeZone: 'America/Santiago', hour: '2-digit', minute: '2-digit', hour12: false });

/** «15:20» en Santiago. */
export function soloHora(iso: string): string {
  const partes = Object.fromEntries(HORA.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${partes.hour.padStart(2, '0')}:${partes.minute}`;
}

function minutos(desde: string, hasta: number): number {
  return Math.round((hasta - Date.parse(desde)) / 60_000);
}

function duracion(total: number): string {
  const horas = Math.floor(total / 60);
  const resto = total % 60;
  if (!horas) return `${resto} min`;
  return resto ? `${horas} h ${resto} min` : `${horas} h`;
}

export function textoVuelo(vuelo: VueloApp, ahora: number = Date.now()): { titulo: string; estado: string; tono: TonoVuelo } {
  const llegada = vuelo.hora_estimada ?? vuelo.hora_programada;
  const demora = vuelo.hora_estimada ? Math.max(0, minutos(vuelo.hora_programada, Date.parse(vuelo.hora_estimada))) : 0;
  switch (vuelo.estado_vuelo) {
    case 'CANCELADO':
      return { titulo: `Vuelo ${vuelo.numero}`, estado: 'cancelado por la aerolínea: consulta a la central', tono: 'error' };
    case 'DESVIADO':
      return { titulo: `Vuelo ${vuelo.numero}`, estado: 'desviado: consulta a la central', tono: 'error' };
    case 'ATERRIZADO':
      return { titulo: `Vuelo ${vuelo.numero} · aterrizó ${soloHora(llegada)}`, estado: `aterrizó hace ${duracion(Math.max(0, minutos(llegada, ahora)))}`, tono: 'neutro' };
  }
  const titulo = `Vuelo ${vuelo.numero} · aterriza ${soloHora(llegada)}`;
  if (demora > 0) return { titulo, estado: `demorado ${duracion(demora)}`, tono: 'aviso' };
  if (vuelo.estado_vuelo === 'DEMORADO') return { titulo, estado: 'demorado', tono: 'aviso' };
  return { titulo, estado: 'a tiempo', tono: 'ok' };
}

export function textoSalida(enAeropuerto: string): string {
  return `El pasajero debe estar en el aeropuerto a las ${soloHora(enAeropuerto)}`;
}
