/**
 * Enlaces para navegar con Google Maps o Waze (HU-17). Son enlaces universales (https): Android los abre en la
 * app instalada y, si no está, en el navegador. Se pasan coordenadas, no la dirección, para no depender de que la
 * otra app la interprete igual.
 */

export interface Punto {
  direccion: string;
  lat: number;
  lon: number;
}

const coordenadas = ({ lat, lon }: Punto) => `${lat.toFixed(6)},${lon.toFixed(6)}`;

export function enlaceGoogleMaps(punto: Punto): string {
  const query = new URLSearchParams({ api: '1', destination: coordenadas(punto), travelmode: 'driving' });
  return `https://www.google.com/maps/dir/?${query.toString()}`;
}

export function enlaceWaze(punto: Punto): string {
  const query = new URLSearchParams({ ll: coordenadas(punto), navigate: 'yes' });
  return `https://waze.com/ul?${query.toString()}`;
}

export interface ViajeActivo {
  id: number;
  estado: 'ACEPTADO' | 'EN_CAMINO' | 'EN_ZONA' | 'PASAJERO_A_BORDO';
  pasajero: string;
  recogida_en: string;
  origen: Punto;
  destino: Punto;
  vuelo: string | null;
  tarifa: number | null;
  convenio: boolean;
  hacia: Punto;
}
