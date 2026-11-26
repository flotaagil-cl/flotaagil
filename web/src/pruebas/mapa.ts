/** HU-71: ayudas para probar el mapa de direcciones (con el mapa de respaldo y sugerencias sin red). */

import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';

export const SUGERENCIAS_MAPA = [
  { texto: 'Av. Providencia 1234, Providencia', lat: -33.4255, lon: -70.6105 },
  { texto: 'Av. Apoquindo 3000, Las Condes', lat: -33.4168, lon: -70.5956 },
];

export const MAPA_CIUDAD = 'Mapa de Santiago';
export const MAPA_AEROPUERTO = 'Mapa con el aeropuerto de Santiago';

/** El portal busca las sugerencias con el `fetch` global; lo demás va por el servidor falso de cada prueba. */
export function simularSugerencias() {
  vi.stubGlobal('fetch', async () => new Response(JSON.stringify({ disponible: true, sugerencias: SUGERENCIAS_MAPA }), { status: 200 }));
}

export async function elegirSugerencia(campo: HTMLElement, indice: number) {
  await userEvent.type(campo, 'avda');
  await userEvent.click((await screen.findAllByRole('option', {}, { timeout: 3000 }))[indice]);
}

/** Nombres de los pines que se ven en el mapa. */
export function pines(nombre: string): string[] {
  return [...screen.getByRole('img', { name: nombre }).querySelectorAll('g[data-tipo] > title')].map((titulo) => titulo.textContent ?? '');
}

export function hayRuta(nombre: string): boolean {
  return screen.getByRole('img', { name: nombre }).querySelector('path[class*="mapaRuta"]') !== null;
}
