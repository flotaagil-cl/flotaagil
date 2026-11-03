import type { EstadoConductor, LicenciaClase } from './api';

export const ESTADOS_CONDUCTOR: Record<EstadoConductor, string> = {
  DISPONIBLE: 'Disponible',
  NO_DISPONIBLE: 'No disponible',
  EN_VIAJE: 'En viaje',
};

export const LICENCIAS: Record<LicenciaClase, string> = {
  A1: 'A1',
  A2: 'A2',
  A3: 'A3',
};

/** Días que faltan para una fecha `AAAA-MM-DD` desde `hoy` (también `AAAA-MM-DD`, en hora de Santiago). */
export function diasHasta(fecha: string, hoy: string): number {
  return Math.round((Date.parse(`${fecha}T00:00:00Z`) - Date.parse(`${hoy}T00:00:00Z`)) / 86_400_000);
}

/** Aviso de la licencia: vencida o por vencer en 30 días; null si está al día. */
export function avisoLicencia(vence: string, hoy: string): string | null {
  const dias = diasHasta(vence, hoy);
  if (dias <= 0) return 'Licencia vencida';
  if (dias <= 30) return dias === 1 ? 'Vence mañana' : `Vence en ${dias} días`;
  return null;
}
