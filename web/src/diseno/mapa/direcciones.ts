/**
 * HU-71: lo que se dibuja en el mapa de un formulario según el tipo de viaje y las coordenadas elegidas. En los
 * viajes de aeropuerto, el extremo del aeropuerto es SCL (salvo que ya tenga un punto guardado). Con un punto, el
 * mapa lo centra; con los dos, los encuadra y los une.
 */

import type { Marcador, PropsMapa, Punto } from './tipos';

export type TipoDeViaje = 'desde-aeropuerto' | 'al-aeropuerto' | 'en-la-ciudad';

/** Como las guardan los formularios y la API (`lon`); el mapa usa `lng`. */
export interface Coordenadas {
  lat: number;
  lon: number;
}

export interface PuntosDelViaje {
  origen: Coordenadas | null;
  destino: Coordenadas | null;
}

export const SIN_PUNTOS: PuntosDelViaje = { origen: null, destino: null };
export const SCL: Punto = { lat: -33.393, lng: -70.794 };
const ETIQUETA_SCL = 'Aeropuerto de Santiago (SCL)';

const aPunto = (c: Coordenadas | null | undefined): Punto | null => (c ? { lat: c.lat, lng: c.lon } : null);

/** `tipo` null: todavía no se elige el tipo de viaje y solo se ve el aeropuerto. */
export function mapaDeDirecciones(tipo: TipoDeViaje | null, origen?: Coordenadas | null, destino?: Coordenadas | null): PropsMapa {
  const etiqueta = tipo === 'en-la-ciudad' ? 'Mapa de Santiago' : 'Mapa con el aeropuerto de Santiago';
  const aeropuerto = (punto: Punto): Marcador => ({ id: 'scl', punto, tipo: 'aeropuerto', etiqueta: ETIQUETA_SCL });
  if (tipo === null) return { etiqueta, marcadores: [aeropuerto(SCL)] };

  const desde = tipo === 'desde-aeropuerto' ? (aPunto(origen) ?? SCL) : aPunto(origen);
  const hasta = tipo === 'al-aeropuerto' ? (aPunto(destino) ?? SCL) : aPunto(destino);
  const marcadores: Marcador[] = [];
  if (desde) {
    marcadores.push(tipo === 'desde-aeropuerto' ? aeropuerto(desde) : { id: 'origen', punto: desde, tipo: 'origen', etiqueta: 'Punto de recogida' });
  }
  if (hasta) {
    marcadores.push(tipo === 'al-aeropuerto' ? aeropuerto(hasta) : { id: 'destino', punto: hasta, tipo: 'destino', etiqueta: 'Destino' });
  }
  return desde && hasta ? { etiqueta, marcadores, ruta: { desde, hasta } } : { etiqueta, marcadores };
}
