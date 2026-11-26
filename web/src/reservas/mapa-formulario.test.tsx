/** HU-71: el mapa del formulario del despachador (nueva reserva y editar). */

import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { hayRuta, MAPA_AEROPUERTO, MAPA_CIUDAD, pines, SUGERENCIAS_MAPA, elegirSugerencia } from '../pruebas/mapa';
import { montarPanel } from '../pruebas/montar';
import type { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { viajeDePrueba } from '../pruebas/servidorViajesFalso';

function conSugerencias(auth: ServidorAuthFalso) {
  const anterior = auth.api;
  auth.api = async (peticion, url) =>
    url.pathname === '/api/direcciones/sugerir/' ? { estado: 200, cuerpo: { disponible: true, sugerencias: SUGERENCIAS_MAPA } } : anterior!(peticion, url);
}

describe('HU-71 · mapa del despachador', () => {
  it('nueva reserva: muestra el punto elegido y, en un viaje de aeropuerto, SCL', async () => {
    const { servidor } = montarPanel('/reservas/nueva');
    conSugerencias(servidor);
    await screen.findByRole('heading', { name: 'Nueva reserva' });
    expect(pines(MAPA_CIUDAD)).toEqual([]);
    await elegirSugerencia(screen.getByRole('combobox', { name: 'Origen' }), 0);
    expect(pines(MAPA_CIUDAD)).toEqual(['Punto de recogida']);
    await userEvent.click(screen.getByRole('radio', { name: /Desde el aeropuerto/i }));
    expect(pines(MAPA_AEROPUERTO)[0]).toBe('Aeropuerto de Santiago (SCL)');
  });

  it('editar: se ven los puntos guardados y escribir a mano quita el pin', async () => {
    const contexto = montarPanel('/reservas/900/editar');
    contexto.viajes.agregar(viajeDePrueba({ id: 900 }));
    const origen = await screen.findByRole('combobox', { name: 'Origen' });
    expect(pines(MAPA_CIUDAD)).toEqual(['Punto de recogida', 'Destino']);
    expect(hayRuta(MAPA_CIUDAD)).toBe(true);
    await userEvent.type(origen, ' depto 2');
    expect(pines(MAPA_CIUDAD)).toEqual(['Destino']);
  });
});
