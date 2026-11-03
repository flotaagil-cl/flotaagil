/** HU-13: el panel refleja el estado que el conductor cambia desde la app, sin recargar (cada 10 s, PR-07). */

import { act, screen, waitFor, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { conductorDePrueba, ServidorFlotaFalso } from '../pruebas/servidorFlotaFalso';
import { REFRESCO_ESTADO_MS } from './api';

afterEach(() => {
  vi.useRealTimers();
});

describe('sincronización del estado del conductor', () => {
  it('el listado y la ficha se actualizan solos cuando el conductor empieza su turno', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const contexto = montarPanel('/conductores', { email: 'admin@andes.example' });
    const flota = new ServidorFlotaFalso(contexto.servidor);
    const conductor = conductorDePrueba({ id: 40, nombre: 'Pedro Soto' });
    flota.conductores.push(conductor);
    await screen.findByRole('columnheader', { name: 'Nombre' });
    expect(within(screen.getByRole('table')).getByText('No disponible')).toBeInTheDocument();

    // El conductor queda Disponible desde la app.
    Object.assign(conductor, { estado: 'DISPONIBLE', vehiculo_activo: { id: 1, patente: 'BCDF10' } });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REFRESCO_ESTADO_MS);
    });
    await waitFor(() => expect(within(screen.getByRole('table')).getByText('Disponible')).toBeInTheDocument());

    await act(async () => {
      await contexto.router.navigate('/conductores/40');
    });
    expect(await screen.findByText(/Disponible · declaró BCDF10/)).toBeInTheDocument();
    Object.assign(conductor, { estado: 'NO_DISPONIBLE', vehiculo_activo: null });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(REFRESCO_ESTADO_MS);
    });
    await waitFor(() => expect(screen.queryByText(/declaró BCDF10/)).not.toBeInTheDocument());
  });
});
