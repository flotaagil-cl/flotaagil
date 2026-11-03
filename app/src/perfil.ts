/** Perfil del conductor (GET /api/app/perfil/) y cuándo debe correr el GPS (RN-18). */

import type { Modo } from './gps/muestreo';

export interface Perfil {
  id: number;
  nombre: string;
  estado: 'DISPONIBLE' | 'NO_DISPONIBLE' | 'EN_VIAJE';
  vehiculo_activo: { id: number; patente: string } | null;
  consentimiento_gps_en: string | null;
  vehiculos: { id: number; patente: string; marca_modelo: string }[];
}

/** Modo del GPS según el perfil, o null si no debe registrar (fuera de turno o sin consentimiento). */
export function modoDeRastreo(perfil: Perfil | null): Modo | null {
  if (!perfil?.consentimiento_gps_en || perfil.estado === 'NO_DISPONIBLE') return null;
  return perfil.estado === 'EN_VIAJE' ? 'viaje' : 'espera';
}

/** Vehículo que se envía al empezar el turno: con uno solo no hace falta elegir (RN-05). */
export function vehiculoParaTurno(perfil: Perfil, elegido: number | null): { listo: boolean; vehiculo?: number } {
  if (perfil.vehiculos.length === 0) return { listo: false };
  if (perfil.vehiculos.length === 1) return { listo: true };
  return elegido === null ? { listo: false } : { listo: true, vehiculo: elegido };
}
