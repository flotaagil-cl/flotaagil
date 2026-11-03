/** Validación de los formularios de flota. Repite las reglas del backend para avisar antes de enviar. */

import { z } from 'zod';
import type { ConductorEditar, VehiculoCrear, VehiculoEditar } from './api';

export const ANTIGUEDAD_MAXIMA = 12;

/** «ab-12 34» → «AB1234», como lo normaliza el backend. */
export function normalizarPatente(valor: string): string {
  return valor.replace(/[^0-9a-z]/gi, '').toUpperCase();
}

/** «12.345.678-k» → «12345678-K». */
export function normalizarRut(valor: string): string {
  return valor.replace(/[.\s]/g, '').toUpperCase();
}

/** «9 1234 5678» o «+56 9 1234-5678» → «+56912345678». Sin prefijo, un móvil de 9 dígitos recibe +56. */
export function normalizarMovil(valor: string): string {
  const limpio = valor.replace(/[^\d+]/g, '');
  return /^9\d{8}$/.test(limpio) ? `+56${limpio}` : limpio;
}

export function digitoVerificador(cuerpo: string): string {
  let suma = 0;
  let factor = 2;
  for (const digito of [...cuerpo].reverse()) {
    suma += Number(digito) * factor;
    factor = factor === 7 ? 2 : factor + 1;
  }
  const resto = 11 - (suma % 11);
  return resto === 11 ? '0' : resto === 10 ? 'K' : String(resto);
}

export function rutValido(rut: string): boolean {
  const partes = /^(\d{7,8})-([\dK])$/.exec(rut);
  return partes !== null && digitoVerificador(partes[1]) === partes[2];
}

const entero = (mensaje: string) =>
  z.string().trim().regex(/^\d+$/, { error: mensaje }).transform(Number);

export function esquemaVehiculo(anioActual: number) {
  const minimo = anioActual - ANTIGUEDAD_MAXIMA;
  return z.object({
    patente: z
      .string()
      .transform(normalizarPatente)
      .refine((p) => /^([A-Z]{2}\d{4}|[A-Z]{4}\d{2})$/.test(p), { error: 'Patente chilena: AB1234 o ABCD12.' }),
    marca_modelo: z
      .string()
      .transform((v) => v.trim().replace(/\s+/g, ' '))
      .refine((v) => v.length > 0, { error: 'Indica la marca y el modelo.' })
      .refine((v) => v.length <= 60, { error: 'Máximo 60 caracteres.' }),
    anio: entero('Indica el año con números.').refine((a) => a >= minimo && a <= anioActual + 1, {
      error: `El vehículo debe ser del año ${minimo} o posterior (antigüedad máxima de ${ANTIGUEDAD_MAXIMA} años).`,
    }),
    capacidad: entero('Indica la capacidad con números.').refine((c) => c >= 1 && c <= 7, {
      error: 'Entre 1 y 7 pasajeros.',
    }),
  });
}

export type ValoresVehiculo = z.input<ReturnType<typeof esquemaVehiculo>>;
export type DatosVehiculo = z.output<ReturnType<typeof esquemaVehiculo>>;

export const VEHICULO_VACIO: ValoresVehiculo = { patente: '', marca_modelo: '', anio: '', capacidad: '4' };

export function cuerpoCrearVehiculo(datos: DatosVehiculo): VehiculoCrear {
  return datos;
}

/** Solo los campos que cambiaron (la patente no se edita). */
export function cuerpoEditarVehiculo(datos: DatosVehiculo, antes: DatosVehiculo): VehiculoEditar {
  const cambios: VehiculoEditar = {};
  if (datos.marca_modelo !== antes.marca_modelo) cambios.marca_modelo = datos.marca_modelo;
  if (datos.anio !== antes.anio) cambios.anio = datos.anio;
  if (datos.capacidad !== antes.capacidad) cambios.capacidad = datos.capacidad;
  return cambios;
}

export function esquemaConductor(hoy: string) {
  return z.object({
    nombre: z
      .string()
      .transform((v) => v.trim().replace(/\s+/g, ' '))
      .refine((v) => v.length > 0, { error: 'Indica el nombre.' })
      .refine((v) => v.length <= 80, { error: 'Máximo 80 caracteres.' }),
    rut: z.string().transform(normalizarRut).refine(rutValido, { error: 'RUT inválido: revisa el dígito verificador.' }),
    telefono: z
      .string()
      .transform(normalizarMovil)
      .refine((t) => /^\+569\d{8}$/.test(t), { error: 'Móvil chileno: +569 y 8 dígitos.' }),
    licencia_clase: z.enum(['A1', 'A2', 'A3'], { error: 'Elige la clase de licencia.' }),
    licencia_vence: z
      .string()
      .regex(/^\d{4}-\d{2}-\d{2}$/, { error: 'Indica la fecha de vencimiento.' })
      .refine((f) => f > hoy, { error: 'La licencia debe estar vigente: la fecha tiene que ser futura.' }),
  });
}

export type ValoresConductor = z.input<ReturnType<typeof esquemaConductor>>;
export type DatosConductor = z.output<ReturnType<typeof esquemaConductor>>;

/** Solo los campos que cambiaron. */
export function cuerpoEditarConductor(datos: DatosConductor, antes: DatosConductor): ConductorEditar {
  return Object.fromEntries(
    (Object.keys(datos) as (keyof DatosConductor)[])
      .filter((campo) => datos[campo] !== antes[campo])
      .map((campo) => [campo, datos[campo]]),
  ) as ConductorEditar;
}
