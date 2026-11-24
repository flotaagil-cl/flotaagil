import type { VueloApp } from './vuelo';

/**
 * Enlaces para navegar con Google Maps o Waze (HU-17). Son enlaces universales (https): Android los abre en la
 * app instalada y, si no está, en el navegador. Con un geocodificador real se pasan coordenadas, para no depender de
 * que la otra app interprete igual la dirección. Con el de desarrollo, que inventa los puntos, se pasa la dirección
 * escrita (DC-30). Lo decide el backend.
 */

export interface Punto {
  direccion: string;
  lat: number;
  lon: number;
}

export type NavegarCon = 'COORDENADAS' | 'DIRECCION';

const coordenadas = ({ lat, lon }: Punto) => `${lat.toFixed(6)},${lon.toFixed(6)}`;

/** %20 y no «+»: se espera que ambas apps lo interpreten igual. */
const parametros = (valores: Record<string, string>) =>
  Object.entries(valores)
    .map(([clave, valor]) => `${clave}=${encodeURIComponent(valor)}`)
    .join('&');

export function enlaceGoogleMaps(punto: Punto, navegarCon: NavegarCon = 'COORDENADAS'): string {
  const destino = navegarCon === 'DIRECCION' ? punto.direccion : coordenadas(punto);
  return `https://www.google.com/maps/dir/?${parametros({ api: '1', destination: destino, travelmode: 'driving' })}`;
}

export function enlaceWaze(punto: Punto, navegarCon: NavegarCon = 'COORDENADAS'): string {
  const destino = navegarCon === 'DIRECCION' ? parametros({ q: punto.direccion }) : parametros({ ll: coordenadas(punto) });
  return `https://waze.com/ul?${destino}&navigate=yes`;
}

export interface ViajeActivo {
  id: number;
  estado: 'ACEPTADO' | 'EN_CAMINO' | 'EN_ZONA' | 'PASAJERO_A_BORDO';
  pasajero: string;
  /** CC-23: nombres de quienes viajan con el pasajero en el mismo vehículo (sin cargos ni teléfonos). */
  acompanantes?: string[];
  recogida_en: string;
  origen: Punto;
  destino: Punto;
  vuelo: string | null;
  /** HU-69: el vuelo de llegada con su estado (null si no hay). */
  detalle_vuelo?: VueloApp | null;
  /** HU-69: en las salidas, la hora a la que el pasajero debe estar en el aeropuerto. */
  en_aeropuerto_a_las?: string | null;
  tarifa: number | null;
  convenio: boolean;
  hacia: Punto;
  navegar_con: NavegarCon;
}
