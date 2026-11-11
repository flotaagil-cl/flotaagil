import e from './diseno.module.css';

export type VarianteBoton = 'principal' | 'secundario' | 'texto' | 'peligro';

/** Clases del botón, también para enlaces que se ven como botón (<Link className={claseBoton()}>). */
export function claseBoton(variante: VarianteBoton = 'principal', ancho = false): string {
  return [e.boton, e[variante], ancho && e.ancho].filter(Boolean).join(' ');
}

/** Iniciales para el logo de la empresa y el avatar: primera letra de las dos primeras palabras. */
export function iniciales(nombre: string): string {
  return nombre
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((palabra) => palabra.charAt(0).toLocaleUpperCase('es-CL'))
    .join('');
}
