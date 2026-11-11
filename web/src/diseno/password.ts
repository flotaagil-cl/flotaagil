/** HU-41: reglas de la contraseña que el pasajero ve mientras escribe. */

export const MINIMO_PASSWORD = 10;

/** Reglas que el pasajero ve mientras escribe (las mismas que valida el backend, salvo las contraseñas comunes). */
export function reglasPassword(nueva: string, repetida: string): { texto: string; cumple: boolean }[] {
  return [
    { texto: `Al menos ${MINIMO_PASSWORD} caracteres`, cumple: nueva.length >= MINIMO_PASSWORD },
    { texto: 'No solo números', cumple: nueva.length > 0 && !/^\d+$/.test(nueva) },
    { texto: 'Las dos contraseñas coinciden', cumple: nueva.length > 0 && nueva === repetida },
  ];
}
