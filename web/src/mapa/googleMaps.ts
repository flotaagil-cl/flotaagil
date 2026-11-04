/**
 * Carga de Google Maps JS y conversión de un conductor a su marcador (PR-12). La clave llega por
 * `VITE_GOOGLE_MAPS_KEY` y nunca se versiona: `web/.env` está ignorado. Al compilar queda en el JavaScript servido,
 * así que debe ir restringida por dominio (`docs/credenciales-externas.md`).
 */

import { confianza, type ConductorMapa, type EstadoConductor } from './estado';

/** Lo que se usa de la API de Google, para no depender de sus tipos completos. */
export interface LatLng {
  lat: number;
  lng: number;
}

export interface MapaGoogleApi {
  fitBounds(limites: LimitesGoogle): void;
  panTo(punto: LatLng): void;
}

export interface LimitesGoogle {
  extend(punto: LatLng): void;
}

export interface MarcadorGoogle {
  setPosition(punto: LatLng): void;
  setTitle(titulo: string): void;
  setLabel(etiqueta: object): void;
  setIcon(icono: object): void;
  setZIndex(indice: number): void;
  setMap(mapa: MapaGoogleApi | null): void;
  addListener(evento: 'click', accion: () => void): void;
}

export interface GoogleMaps {
  Map: new (elemento: HTMLElement, opciones: object) => MapaGoogleApi;
  Marker: new (opciones: object) => MarcadorGoogle;
  LatLngBounds: new () => LimitesGoogle;
  SymbolPath: { CIRCLE: unknown };
}

interface VentanaConGoogle {
  google?: { maps?: GoogleMaps };
  gm_authFailure?: () => void;
  __flotaagilMapaListo?: () => void;
}

const RUTA = 'https://maps.googleapis.com/maps/api/js';

let carga: Promise<GoogleMaps> | null = null;
const alFallarClave = new Set<() => void>();

/** Se llama si Google rechaza la clave después de cargar (restricción, facturación). Devuelve cómo darse de baja. */
export function alRechazarClave(oyente: () => void): () => void {
  alFallarClave.add(oyente);
  return () => alFallarClave.delete(oyente);
}

/** Carga el script una sola vez; si falla, un nuevo intento vuelve a pedirlo. */
export function cargarGoogleMaps(clave: string): Promise<GoogleMaps> {
  if (carga) return carga;
  const ventana = window as unknown as VentanaConGoogle;
  carga = new Promise<GoogleMaps>((resolver, rechazar) => {
    // Google llama a esta función global cuando rechaza la clave, incluso después de cargar.
    ventana.gm_authFailure = () => alFallarClave.forEach((oyente) => oyente());
    ventana.__flotaagilMapaListo = () => {
      if (ventana.google?.maps) resolver(ventana.google.maps);
      else rechazar(new Error('Google Maps no quedó disponible.'));
    };
    const script = document.createElement('script');
    script.src = `${RUTA}?${new URLSearchParams({
      key: clave,
      v: 'quarterly',
      language: 'es',
      region: 'CL',
      loading: 'async',
      callback: '__flotaagilMapaListo',
    }).toString()}`;
    script.async = true;
    script.onerror = () => {
      script.remove();
      rechazar(new Error('No se pudo cargar Google Maps.'));
    };
    document.head.append(script);
  }).catch((error: unknown) => {
    carga = null;
    throw error;
  });
  return carga;
}

/** Solo para las pruebas: cada una parte sin script cargado. */
export function olvidarCargaDeGoogleMaps() {
  carga = null;
  alFallarClave.clear();
}

/** Mismos colores que el mapa esquemático (`mapa.module.css`). */
const COLORES: Record<EstadoConductor, string> = { DISPONIBLE: '#15803d', EN_VIAJE: '#b45309' };
const COLOR_NO_CONFIABLE = '#9ca3af';

export interface DatosMarcador {
  posicion: LatLng;
  titulo: string;
  etiqueta: string;
  color: string;
  opacidad: number;
  escala: number;
  seleccionado: boolean;
}

/** Datos del marcador; null si el conductor todavía no tiene posición. */
export function datosMarcador(conductor: ConductorMapa, seleccionado: number | null, ahora: number): DatosMarcador | null {
  if (!conductor.posicion) return null;
  const { confiable } = confianza(conductor, ahora);
  const activo = conductor.id === seleccionado;
  return {
    posicion: { lat: conductor.posicion.lat, lng: conductor.posicion.lon },
    titulo: conductor.nombre,
    etiqueta: conductor.patente ?? conductor.nombre.split(' ')[0],
    color: confiable ? COLORES[conductor.estado] : COLOR_NO_CONFIABLE,
    opacidad: confiable ? 1 : 0.55,
    escala: activo ? 13 : 10,
    seleccionado: activo,
  };
}
