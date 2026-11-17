/** HU-54 (CC-22): el contacto del convenio autoriza o rechaza una reserva pública. CP-51. */

import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonPortal, montarPortal } from '../pruebas/montarPortal';

const VIAJE = { id: 501, recogida_en: '2026-11-20T13:00:00Z', origen_dir: 'Origen', destino_dir: 'Destino' };

describe('HU-54 · autorizar la reserva', () => {
  it.each([
    ['Autorizar', 'SOLICITADO', 'Reserva autorizada'],
    ['Rechazar', 'CANCELADO', 'Reserva rechazada'],
  ])('«%s» envía la decisión y muestra el resultado', async (boton, estado, titulo) => {
    const { peticiones } = montarPortal('/solicitar/transportes-andes/autorizar/abc:firma', {
      responder: (_p, ruta) => (ruta.endsWith('/reservas/autorizar/') ? jsonPortal(200, { ...VIAJE, estado }) : undefined),
    });
    await userEvent.click(await screen.findByRole('button', { name: boton }));
    expect(await screen.findByRole('heading', { name: titulo })).toBeInTheDocument();
    expect(peticiones[0].cuerpo).toEqual({ token: 'abc:firma', decision: boton.toLowerCase() });
  });

  it('no decide al abrir el enlace y explica un enlace ya usado', async () => {
    const { peticiones } = montarPortal('/solicitar/transportes-andes/autorizar/abc:firma', {
      responder: (_p, ruta) => (ruta.endsWith('/reservas/autorizar/') ? jsonPortal(409, { detail: 'x' }) : undefined),
    });
    await screen.findByRole('heading', { name: '¿Autorizas esta reserva?' });
    expect(peticiones).toHaveLength(0);
    await userEvent.click(screen.getByRole('button', { name: 'Autorizar' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('ya no está pendiente'));
  });
});
