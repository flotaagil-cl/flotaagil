/** HU-56 (CC-22): encuesta por correo y avisos sin WhatsApp para las empresas sin el módulo. CP-52. */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
// import { entradasDeMenu, crearRutas } from '../rutas/tabla';
import { jsonPortal, montarPortal } from '../pruebas/montarPortal';

describe('HU-56 · encuesta por correo', () => {
  it('registra el puntaje elegido y agradece', async () => {
    const { peticiones } = montarPortal('/solicitar/transportes-andes/encuesta/abc:firma', {
      responder: (_p, ruta) => (ruta.endsWith('/encuesta/') ? jsonPortal(201, { puntaje: 4 }) : undefined),
    });
    const grupo = await screen.findByRole('group', { name: 'Calificación' });
    expect(peticiones).toHaveLength(0);
    await userEvent.click(within(grupo).getByRole('button', { name: '4 estrellas' }));
    expect(await screen.findByRole('heading', { name: '¡Gracias por tu opinión!' })).toBeInTheDocument();
    expect(peticiones[0].cuerpo).toEqual({ token: 'abc:firma', puntaje: 4 });
  });

  it.each([
    [409, 'Este viaje ya tenía tu calificación.'],
    [400, 'El enlace no es válido o ya venció.'],
  ])('responde %i', async (estado, texto) => {
    montarPortal('/solicitar/transportes-andes/encuesta/abc:firma', {
      responder: (_p, ruta) => (ruta.endsWith('/encuesta/') ? jsonPortal(estado, { detail: 'x' }) : undefined),
    });
    await userEvent.click(await screen.findByRole('button', { name: '5 estrellas' }));
    expect(await screen.findByText(texto)).toBeInTheDocument();
  });
});

/* Oculto del menú del panel (sin borrar código).
describe('HU-56 · Conversaciones solo con el módulo de cuentas', () => {
  it.each([
    [true, true],
    [false, false],
  ])('con módulo %s, el menú muestra Conversaciones: %s', (modulo, visible) => {
    const titulos = entradasDeMenu(crearRutas(), 'DESPACHADOR', '', modulo).map((e) => e.titulo);
    expect(titulos.includes('Historial WhatsApp')).toBe(visible);
    expect(titulos).toContain('Reservas');
  });
});
*/
