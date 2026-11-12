/** HU-45: funciones puras de «Mi perfil», para probarlas sin pantallas. */

/** Lo que el pasajero escribe para confirmar que quiere eliminar su cuenta. */
export const PALABRA_ELIMINAR = 'ELIMINAR';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sept', 'oct', 'nov', 'dic'];

/** «oct 2026» a partir de un instante ISO. Toma el mes del texto (UTC): para «Pasajero desde» basta. */
export function mesYAnio(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const [anio, mes] = iso.slice(0, 7).split('-');
  return `${MESES[Number(mes) - 1]} ${anio}`;
}

/** «+56 9 1234 5678» para los números chilenos; el resto queda como viene. */
export function telefonoLegible(telefono: string): string {
  const m = /^\+569(\d{4})(\d{4})$/.exec(telefono);
  return m ? `+56 9 ${m[1]} ${m[2]}` : telefono;
}
