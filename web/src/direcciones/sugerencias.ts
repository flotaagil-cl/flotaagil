/**
 * HU-71 (DC-72): sugerencias de direcciones a través del backend (`/api/direcciones/sugerir/`), que consulta Photon
 * con caché y límite. Si el servicio no responde o está en «ninguno», no hay sugerencias y el campo sigue como texto.
 */

export interface Coordenadas {
  lat: number;
  lon: number;
}

export interface Sugerencia extends Coordenadas {
  texto: string;
}

export type Buscar = (texto: string, senal: AbortSignal) => Promise<Sugerencia[]>;

export const MINIMO_CARACTERES = 3;
export const ESPERA_MS = 300;
export const MAXIMO = 5;

function lista(cuerpo: unknown): Sugerencia[] {
  const sugerencias = (cuerpo as { sugerencias?: unknown } | null)?.sugerencias;
  if (!Array.isArray(sugerencias)) return [];
  return sugerencias
    .filter((s): s is Sugerencia => typeof s?.texto === 'string' && typeof s?.lat === 'number' && typeof s?.lon === 'number')
    .slice(0, MAXIMO);
}

/** Formularios públicos y del portal: sin sesión, con el slug de la empresa (límite por IP en el backend). */
export function buscarPublico(slug: string): Buscar {
  return async (texto, senal) => {
    const consulta = new URLSearchParams({ q: texto, empresa: slug });
    const respuesta = await fetch(`/api/direcciones/sugerir/?${consulta.toString()}`, { signal: senal, credentials: 'omit' });
    return respuesta.ok ? lista(await respuesta.json()) : [];
  };
}

/** Panel: con la sesión (el backend centra en la zona de la empresa y limita por usuario). */
export function buscarConSesion(pedir: (texto: string, senal: AbortSignal) => Promise<{ data?: unknown; response: Response }>): Buscar {
  return async (texto, senal) => {
    const { data, response } = await pedir(texto, senal);
    return response.ok ? lista(data) : [];
  };
}
