/** Respuestas rápidas del conductor (CC-19): la app manda el código y el servidor pone el texto. */
export const RAPIDAS = [
  { codigo: 'EN_CAMINO', texto: 'Voy en camino' },
  { codigo: 'LLEGUE', texto: 'Llegué' },
  { codigo: 'NO_APARECE', texto: 'Pasajero no aparece' },
  { codigo: 'ATRASO', texto: 'Me atraso 10 min' },
  { codigo: 'AYUDA', texto: 'Necesito ayuda' },
] as const;
