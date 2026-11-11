import type { ComponentType } from 'react';

export interface Punto {
  lat: number;
  lng: number;
}

export type TipoMarcador = 'aeropuerto' | 'origen' | 'destino' | 'vehiculo';

export interface Marcador {
  id: string;
  punto: Punto;
  tipo: TipoMarcador;
  etiqueta: string;
}

/**
 * Lo que una pantalla le pide a un mapa. El de respaldo y el real (Google Maps, más adelante) reciben lo mismo:
 * las pantallas no cambian al reemplazarlo.
 */
export interface PropsMapa {
  /** Descripción para lectores de pantalla («Mapa: aeropuerto y destino»). */
  etiqueta: string;
  marcadores: Marcador[];
  ruta?: { desde: Punto; hasta: Punto };
}

export type ComponenteMapa = ComponentType<PropsMapa>;
