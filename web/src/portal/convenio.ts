/**
 * CC-23 (HU-73): reserva de convenio con correo + clave en el portal base (sin módulo de cuentas).
 *
 * El pase que entrega el servidor vive en `sessionStorage` (se borra al cerrar la pestaña) y nunca la clave.
 * Si vence, el servidor responde 401 y el formulario vuelve al paso de la clave.
 */

import type { components } from '../api/esquema';

export type PaseConvenio = components['schemas']['PaseConvenioRespuesta'];
export type Para = components['schemas']['ParaEnum'];
export type Vehiculos = components['schemas']['VehiculosEnum'];

export interface Persona {
  nombre: string;
  cargo: string;
  telefono: string;
  correo: string;
}

export const PERSONA_VACIA: Persona = { nombre: '', cargo: '', telefono: '', correo: '' };

export interface DatosConvenio {
  para: Para;
  pasajero: Persona;
  acompanado: boolean;
  vehiculos: Vehiculos;
  acompanantes: Persona[];
  declara_informados: boolean;
}

export const DATOS_CONVENIO: DatosConvenio = {
  para: 'MI',
  pasajero: PERSONA_VACIA,
  acompanado: false,
  vehiculos: 'MISMO',
  acompanantes: [],
  declara_informados: false,
};

const CLAVE_SESION = (slug: string) => `flotaagil:pase-convenio:${slug}`;

function almacen(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function leerPase(slug: string): PaseConvenio | null {
  try {
    const crudo = almacen()?.getItem(CLAVE_SESION(slug));
    if (!crudo) return null;
    const pase = JSON.parse(crudo) as PaseConvenio;
    return Date.parse(pase.vence_en) > Date.now() ? pase : null;
  } catch {
    return null;
  }
}

export function guardarPase(slug: string, pase: PaseConvenio): void {
  try {
    almacen()?.setItem(CLAVE_SESION(slug), JSON.stringify(pase));
  } catch {
    // Sin almacenamiento (modo privado): el pase vive solo en la página.
  }
}

export function borrarPase(slug: string): void {
  try {
    almacen()?.removeItem(CLAVE_SESION(slug));
  } catch {
    // nada que borrar
  }
}

/** Personas que viajan: el pasajero principal (quien pide u otra persona) más los acompañantes. */
export function totalPersonas(d: DatosConvenio): number {
  return 1 + (d.acompanado ? d.acompanantes.length : 0);
}

/** Máximo de acompañantes: en el mismo vehículo, la capacidad; separados, el tope por solicitud. */
export function maximoAcompanantes(d: DatosConvenio, capacidad: number, tope: number): number {
  return Math.max(0, (d.vehiculos === 'MISMO' ? capacidad : tope) - 1);
}

export type ErroresConvenio = Partial<Record<string, string>>;

const CORREO = /^\S+@\S+\.\S+$/;

/** Errores por campo: `pasajero.nombre`, `acompanantes.0.telefono`, `declara_informados`… CC-26: el pasajero con
 * cuenta no informa cargo (`conCargo: false`). */
export function validarConvenio(d: DatosConvenio, capacidad: number, tope: number, { conCargo = true } = {}): ErroresConvenio {
  const errores: ErroresConvenio = {};
  const persona = (p: Persona, prefijo: string, telefonoObligatorio: boolean) => {
    if (!p.nombre.trim()) errores[`${prefijo}.nombre`] = 'Escribe el nombre.';
    if (conCargo && !p.cargo.trim()) errores[`${prefijo}.cargo`] = 'Escribe el cargo.';
    if (telefonoObligatorio && !p.telefono.trim()) errores[`${prefijo}.telefono`] = 'Escribe el teléfono.';
    if (p.correo.trim() && !CORREO.test(p.correo.trim())) errores[`${prefijo}.correo`] = 'Revisa el correo.';
  };
  if (d.para === 'OTRO') persona(d.pasajero, 'pasajero', true);
  if (d.acompanado) {
    if (d.acompanantes.length === 0) errores.acompanantes = 'Agrega al menos un acompañante.';
    d.acompanantes.forEach((a, i) => persona(a, `acompanantes.${i}`, d.vehiculos === 'SEPARADOS'));
    if (d.acompanantes.length > maximoAcompanantes(d, capacidad, tope)) {
      errores.acompanantes =
        d.vehiculos === 'MISMO'
          ? `En un vehículo caben ${capacidad} personas. Elige «Vehículos separados» para el resto.`
          : `Puedes pedir para hasta ${tope} personas por solicitud.`;
    }
  }
  if ((d.para === 'OTRO' || (d.acompanado && d.acompanantes.length > 0)) && !d.declara_informados) {
    errores.declara_informados = 'Declara que informaste a las personas que viajan.';
  }
  return errores;
}

const limpia = (p: Persona) => ({
  nombre: p.nombre.trim(),
  cargo: p.cargo.trim(),
  telefono: p.telefono.trim(),
  correo: p.correo.trim(),
});

/** Quién viaja: los mismos campos con el pase (CC-23) y con la cuenta del convenio (CC-25). */
export function cuerpoPersonas(d: DatosConvenio) {
  const acompanantes = d.acompanado ? d.acompanantes.map(limpia) : [];
  const otro = d.para === 'OTRO' ? limpia(d.pasajero) : null;
  return {
    para: d.para,
    pasajero_nombre: otro?.nombre ?? '',
    pasajero_cargo: otro?.cargo ?? '',
    pasajero_telefono: otro?.telefono ?? '',
    pasajero_correo: otro?.correo ?? '',
    acompanantes,
    vehiculos: acompanantes.length ? d.vehiculos : ('MISMO' as Vehiculos),
    declara_informados: d.declara_informados,
  };
}

/** Campos que se suman al cuerpo de la reserva pública cuando se pide con el pase. */
export function cuerpoConvenio(d: DatosConvenio, pase: string) {
  return { pase, ...cuerpoPersonas(d), es_empresa: false };
}

/** Errores del servidor (400) a la forma de `validarConvenio`. */
export function erroresConvenioDelServidor(cuerpo: unknown): ErroresConvenio {
  const salida: ErroresConvenio = {};
  if (!cuerpo || typeof cuerpo !== 'object') return salida;
  const primero = (v: unknown) => (Array.isArray(v) ? (typeof v[0] === 'string' ? v[0] : null) : typeof v === 'string' ? v : null);
  for (const [campo, valor] of Object.entries(cuerpo as Record<string, unknown>)) {
    const directo = primero(valor);
    if (campo.startsWith('pasajero_') && directo) salida[`pasajero.${campo.slice('pasajero_'.length)}`] = directo;
    else if (campo === 'acompanantes' && Array.isArray(valor) && valor.some((v) => v && typeof v === 'object')) {
      valor.forEach((item, i) => {
        if (item && typeof item === 'object') {
          for (const [sub, mensajes] of Object.entries(item as Record<string, unknown>)) {
            const texto = primero(mensajes);
            if (texto) salida[`acompanantes.${i}.${sub}`] = texto;
          }
        }
      });
    } else if ((campo === 'acompanantes' || campo === 'declara_informados') && directo) salida[campo] = directo;
  }
  return salida;
}
