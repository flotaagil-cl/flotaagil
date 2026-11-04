/** Horas en America/Santiago, sin depender de la zona del teléfono. */
const FORMATO = new Intl.DateTimeFormat('es-CL', {
  timeZone: 'America/Santiago',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
});

export const horaDeChile = (iso: string) => FORMATO.format(new Date(iso));

const FECHA_Y_HORA = new Intl.DateTimeFormat('es-CL', {
  timeZone: 'America/Santiago',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

/** «04-11 12:30»: un turno puede cruzar la medianoche. */
export function fechaYHora(iso: string): string {
  const partes = Object.fromEntries(FECHA_Y_HORA.formatToParts(new Date(iso)).map((p) => [p.type, p.value]));
  return `${partes.day.padStart(2, '0')}-${partes.month.padStart(2, '0')} ${partes.hour.padStart(2, '0')}:${partes.minute}`;
}

export const pesos = (monto: number) => `$${monto.toLocaleString('es-CL')}`;
