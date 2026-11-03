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
