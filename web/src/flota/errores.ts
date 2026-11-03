/** Errores de /api/vehiculos/ y /api/conductores/ para la interfaz. */

import { MENSAJES } from '../api/errores';
import { erroresDelBackend as erroresDrf, type ErroresFormulario } from '../api/erroresDrf';
import { detalleDe, ErrorApi } from '../api/resultado';

/** Los campos de la API se llaman igual en los formularios de flota. */
export function erroresDelBackend(cuerpo: unknown, permitidos: readonly string[]): ErroresFormulario {
  return erroresDrf(cuerpo, Object.fromEntries(permitidos.map((campo) => [campo, campo])), permitidos);
}

/** Mensaje para un error de consulta o de una acción. `que`: «el vehículo», «el conductor». */
export function mensajeDeError(error: unknown, que = 'el registro'): string {
  if (!(error instanceof ErrorApi)) return MENSAJES.inesperado;
  const { estado } = error;
  if (estado === 0 || estado === 502 || estado === 503 || estado === 504) return MENSAJES.sin_conexion;
  if (estado === 404) return `No se encontró ${que}.`;
  if (estado === 403) return 'Solo el administrador de la empresa administra la flota.';
  if (estado === 401) return MENSAJES.sesion_terminada;
  if (estado >= 500) return MENSAJES.error_servidor;
  return detalleDe(error) ?? MENSAJES.inesperado;
}
