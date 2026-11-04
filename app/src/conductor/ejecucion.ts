/**
 * Lógica de los botones del viaje en curso (HU-16): qué paso sigue según el estado y validación del pago (RN-10).
 * EN_ZONA lo marca el backend por geocerca; el botón siguiente es el mismo en EN_CAMINO y en EN_ZONA, porque si el
 * GPS no alcanza la precisión necesaria el conductor no debe quedar bloqueado (DC-17).
 */

export type EstadoEnCurso = 'ACEPTADO' | 'EN_CAMINO' | 'EN_ZONA' | 'PASAJERO_A_BORDO';
export type Accion = 'en-camino' | 'a-bordo';
export type MetodoPago = 'EFECTIVO' | 'TARJETA' | 'TRANSFERENCIA' | 'CONVENIO';

export const MONTO_MAXIMO = 500_000;

const PASOS: Record<Exclude<EstadoEnCurso, 'PASAJERO_A_BORDO'>, { accion: Accion; texto: string; enviando: string }> = {
  ACEPTADO: { accion: 'en-camino', texto: 'Voy en camino', enviando: 'Registrando…' },
  EN_CAMINO: { accion: 'a-bordo', texto: 'Pasajero a bordo', enviando: 'Registrando…' },
  EN_ZONA: { accion: 'a-bordo', texto: 'Pasajero a bordo', enviando: 'Registrando…' },
};

/** Paso siguiente, o null cuando lo que sigue es el formulario de pago. */
export function pasoSiguiente(estado: EstadoEnCurso) {
  return estado === 'PASAJERO_A_BORDO' ? null : PASOS[estado];
}

/** El método Convenio solo existe para los viajes de un convenio. */
export function metodosDePago(convenio: boolean): { valor: MetodoPago; texto: string }[] {
  const metodos: { valor: MetodoPago; texto: string }[] = [
    { valor: 'EFECTIVO', texto: 'Efectivo' },
    { valor: 'TARJETA', texto: 'Tarjeta' },
    { valor: 'TRANSFERENCIA', texto: 'Transferencia' },
  ];
  return convenio ? [{ valor: 'CONVENIO', texto: 'Convenio' }, ...metodos] : metodos;
}

export const nombreDelMetodo = (metodo: MetodoPago) => metodosDePago(true).find((m) => m.valor === metodo)!.texto;

export type ResultadoMonto = { monto: number; error?: undefined } | { monto?: undefined; error: string };

/** Acepta «15000» y «15.000». Pesos enteros, de 0 a 500.000 (PAGO_VIAJE). */
export function leerMonto(texto: string): ResultadoMonto {
  const limpio = texto.trim().replace(/[.\s]/g, '').replace(/^\$/, '');
  if (!limpio) return { error: 'Ingresa el monto cobrado.' };
  if (!/^\d+$/.test(limpio)) return { error: 'El monto debe ser un número entero, sin decimales.' };
  const monto = Number(limpio);
  if (monto > MONTO_MAXIMO) return { error: 'El monto máximo es $500.000.' };
  return { monto };
}
