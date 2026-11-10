import type { ConvenioDetalle } from './api';

/** HU-34: estados del convenio para mostrar. */
export const ESTADOS_CONVENIO: Record<ConvenioDetalle['estado'], string> = {
  EN_REVISION: 'En revisión',
  APROBADO: 'Aprobado',
  RECHAZADO: 'Rechazado',
  INACTIVO: 'Inactivo',
};
