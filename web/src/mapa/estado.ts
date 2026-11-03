/**
 * Estado del mapa en tiempo real (HU-02): conductores en turno con su última posición, armado con los mensajes
 * del WebSocket /ws/mapa/. Funciones puras para probarlas sin navegador.
 */

export type EstadoConductor = 'DISPONIBLE' | 'EN_VIAJE';

export interface Posicion {
  lat: number;
  lon: number;
  precision_m: number | null;
  registrada_en: string;
}

export interface ConductorMapa {
  id: number;
  nombre: string;
  estado: EstadoConductor;
  patente: string | null;
  posicion: Posicion | null;
}

export type Mensaje =
  | { tipo: 'inicial'; conductores: ConductorMapa[] }
  | { tipo: 'conductor'; conductor: ConductorMapa }
  | { tipo: 'fuera'; id: number }
  | { tipo: 'pong' };

/** HU-02: una posición de más de 60 s se marca como no confiable (igual que POSICION_CONFIABLE_SEGUNDOS). */
export const MAXIMO_SEGUNDOS = 60;
/** Anexo D: precisión mayor a 100 m = no confiable. */
export const PRECISION_MAXIMA_M = 100;

export type Confianza = { confiable: true } | { confiable: false; motivo: 'sin_posicion' | 'antigua' | 'imprecisa' };

export function confianza(conductor: ConductorMapa, ahora: number): Confianza {
  const posicion = conductor.posicion;
  if (!posicion) return { confiable: false, motivo: 'sin_posicion' };
  if (ahora - Date.parse(posicion.registrada_en) > MAXIMO_SEGUNDOS * 1000) return { confiable: false, motivo: 'antigua' };
  if (posicion.precision_m !== null && posicion.precision_m > PRECISION_MAXIMA_M) return { confiable: false, motivo: 'imprecisa' };
  return { confiable: true };
}

/** Segundos desde la última posición, o null si no tiene. */
export function antiguedad(conductor: ConductorMapa, ahora: number): number | null {
  return conductor.posicion ? Math.max(0, Math.round((ahora - Date.parse(conductor.posicion.registrada_en)) / 1000)) : null;
}

export function aplicar(conductores: ReadonlyMap<number, ConductorMapa>, mensaje: Mensaje): Map<number, ConductorMapa> {
  if (mensaje.tipo === 'inicial') return new Map(mensaje.conductores.map((c) => [c.id, c]));
  const nuevos = new Map(conductores);
  if (mensaje.tipo === 'conductor') {
    const anterior = nuevos.get(mensaje.conductor.id);
    // Un aviso tardío no reemplaza una posición más reciente (los mensajes pueden llegar desordenados).
    const masNueva =
      anterior?.posicion && mensaje.conductor.posicion && Date.parse(anterior.posicion.registrada_en) > Date.parse(mensaje.conductor.posicion.registrada_en);
    nuevos.set(mensaje.conductor.id, masNueva ? { ...mensaje.conductor, posicion: anterior.posicion } : mensaje.conductor);
  }
  if (mensaje.tipo === 'fuera') nuevos.delete(mensaje.id);
  return nuevos;
}

export interface Encuadre {
  latMin: number;
  latMax: number;
  lonMin: number;
  lonMax: number;
}

/** Santiago (centro) por defecto; si hay posiciones, las encuadra con margen y un tamaño mínimo (~2 km). */
export function encuadre(conductores: Iterable<ConductorMapa>): Encuadre {
  const puntos = [...conductores].flatMap((c) => (c.posicion ? [c.posicion] : []));
  if (!puntos.length) return { latMin: -33.55, latMax: -33.35, lonMin: -70.75, lonMax: -70.55 };
  const lats = puntos.map((p) => p.lat);
  const lons = puntos.map((p) => p.lon);
  const centro = (a: number[]) => (Math.min(...a) + Math.max(...a)) / 2;
  const medio = (a: number[]) => Math.max((Math.max(...a) - Math.min(...a)) / 2 * 1.2, 0.01);
  const [lat, lon, dLat, dLon] = [centro(lats), centro(lons), medio(lats), medio(lons)];
  return { latMin: lat - dLat, latMax: lat + dLat, lonMin: lon - dLon, lonMax: lon + dLon };
}
