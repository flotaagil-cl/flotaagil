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
