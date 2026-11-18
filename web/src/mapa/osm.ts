/**
 * HU-70 (DC-71): OpenStreetMap con Leaflet, solo para desarrollo y pruebas. Teselas públicas de
 * tile.openstreetmap.org con la atribución visible, según su política de uso: sin precarga ni descarga masiva
 * (Leaflet pide solo las teselas a la vista), con el Referer del sitio y sin pasar de su zoom máximo (19).
 */

import type * as Leaflet from 'leaflet';

export type L = typeof Leaflet;

export const TESELAS_OSM = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
export const ATRIBUCION_OSM = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
/** Teselas que fallan antes de que cargue alguna: sin internet o bloqueadas, se vuelve al esquemático. */
export const FALLAS_PARA_RENDIRSE = 3;

let carga: Promise<L> | null = null;

/** Carga Leaflet (y su CSS) una sola vez, en un trozo aparte: no pesa en las pantallas que no tienen mapa. */
export function cargarLeaflet(): Promise<L> {
  carga ??= Promise.all([import('leaflet'), import('leaflet/dist/leaflet.css')])
    .then(([modulo]) => ((modulo as unknown as { default?: L }).default ?? (modulo as unknown as L)))
    .catch((error: unknown) => {
      carga = null;
      throw error;
    });
  return carga;
}

/** Solo para las pruebas: cada una parte sin Leaflet cargado. */
export function olvidarCargaDeLeaflet() {
  carga = null;
}

/** Capa de teselas de OSM que avisa si no logra cargar ninguna. */
export function capaOsm(leaflet: L, alFallar: () => void): Leaflet.TileLayer {
  const capa = leaflet.tileLayer(TESELAS_OSM, {
    maxZoom: 19,
    attribution: ATRIBUCION_OSM,
    // Sin precarga: solo la vista actual, y no pide teselas mientras se hace zoom.
    keepBuffer: 1,
    updateWhenZooming: false,
  });
  let cargadas = 0;
  let fallas = 0;
  capa.on('tileload', () => {
    cargadas += 1;
  });
  capa.on('tileerror', () => {
    fallas += 1;
    if (cargadas === 0 && fallas === FALLAS_PARA_RENDIRSE) alFallar();
  });
  return capa;
}
