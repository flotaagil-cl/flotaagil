/**
 * HU-70 (DC-71): qué mapa se dibuja. `VITE_MAPA_PROVEEDOR` = google | osm | esquematico manda; sin él, Google si hay
 * `VITE_GOOGLE_MAPS_KEY` y, si no, OpenStreetMap en desarrollo (en producción, el esquemático). Google sigue siendo
 * el de producción; OSM es solo para desarrollo y pruebas.
 */

export type ProveedorMapa = 'google' | 'osm' | 'esquematico';

export interface EntornoMapa {
  VITE_MAPA_PROVEEDOR?: string;
  VITE_GOOGLE_MAPS_KEY?: string;
  DEV?: boolean;
}

export function elegirProveedor(entorno: EntornoMapa): ProveedorMapa {
  const pedido = (entorno.VITE_MAPA_PROVEEDOR ?? '').trim().toLowerCase();
  const clave = Boolean(entorno.VITE_GOOGLE_MAPS_KEY);
  if (pedido === 'google') return clave ? 'google' : 'esquematico';
  if (pedido === 'osm' || pedido === 'esquematico') return pedido;
  if (clave) return 'google';
  return entorno.DEV ? 'osm' : 'esquematico';
}

export function proveedorDelEntorno(): ProveedorMapa {
  return elegirProveedor(import.meta.env as EntornoMapa);
}
