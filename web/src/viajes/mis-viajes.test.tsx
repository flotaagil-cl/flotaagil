/** HU-44: «Mis viajes» y cancelar según RN-09. */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { VIAJE } from './tu-viaje.test';
import { esAnterior, tramo, type MiViaje } from './viaje';

const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

const fila = (cambios: Partial<MiViaje>): MiViaje => ({
  id: 1,
  estado: 'SOLICITADO',
  estado_texto: 'Solicitado',
  canal: 'WEB',
  sentido: 'URBANO',
  origen_dir: 'Av. Providencia 1208, Providencia',
  destino_dir: 'Plaza de Armas, Santiago',
  recogida_en: '2026-11-13T21:40:00Z',
  cancelable: true,
  historial: [],
  ...cambios,
});

const LISTA = [
  fila({ id: 20533, sentido: 'HACIA_AEROPUERTO', destino_dir: 'Aeropuerto de Santiago (SCL)', recogida_en: '2026-11-24T08:40:00Z' }),
  fila({ id: 20481, sentido: 'DESDE_AEROPUERTO', origen_dir: 'Aeropuerto de Santiago (SCL)', destino_dir: 'Hotel Cumbres, Vitacura', estado: 'EN_CAMINO', cancelable: false }),
  fila({ id: 19870, estado: 'FINALIZADO', cancelable: false }),
  fila({ id: 19422, estado: 'CANCELADO', cancelable: false }),
];

function montar(ruta: string, { detalle = VIAJE, cancelar = [] as (() => Response)[] } = {}) {
  const servidor = new ServidorAuthFalso();
  const cancelaciones: unknown[] = [];
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const { pathname } = new URL(peticion.url);
    if (pathname === '/api/mi-cuenta/reservas/') return json(200, { count: LISTA.length, next: null, previous: null, results: LISTA });
    if (pathname.endsWith('/cancelar/')) {
      cancelaciones.push(await peticion.json());
      const siguiente = cancelar.shift();
      return siguiente ? siguiente() : json(200, fila({ id: detalle.id, estado: 'CANCELADO', cancelable: false }));
    }
    if (pathname.startsWith('/api/mi-cuenta/reservas/')) return json(200, detalle);
    return original(peticion);
  };
  return { ...montarPanel(ruta, { email: 'pasajero@andes.example', servidor }), cancelaciones };
}

describe('HU-44 · funciones', () => {
  it('anteriores y tramo corto', () => {
    expect([esAnterior('FINALIZADO'), esAnterior('CANCELADO'), esAnterior('EN_CAMINO'), esAnterior(undefined)]).toEqual([true, true, false, false]);
    expect(tramo(LISTA[0])).toBe('Av. Providencia 1208 → SCL');
    expect(tramo(LISTA[1])).toBe('SCL → Hotel Cumbres');
    expect(tramo(LISTA[2])).toBe('Av. Providencia 1208 → Plaza de Armas');
  });
});

describe('HU-44 · mis viajes', () => {
  it('próximos ordenados por recogida y anteriores; cada uno abre su viaje', async () => {
    montar('/mis-viajes');
    expect(await screen.findByRole('heading', { name: 'Mis viajes' })).toBeInTheDocument();
    const proximos = await screen.findByRole('radio', { name: 'Próximos (2)' });
    expect(proximos).toBeChecked();
    const enlaces = within(screen.getByRole('list')).getAllByRole('link');
    expect(enlaces.map((a) => a.getAttribute('href'))).toEqual(['/mis-viajes/20481', '/mis-viajes/20533']);
    expect(enlaces[0]).toHaveTextContent('SCL → Hotel Cumbres');
    expect(enlaces[0]).toHaveTextContent('Conductor en camino');
    await userEvent.click(screen.getByRole('radio', { name: 'Anteriores' }));
    const anteriores = within(screen.getByRole('list')).getAllByRole('link');
    expect(anteriores.map((a) => a.textContent)).toEqual([expect.stringContaining('Finalizado'), expect.stringContaining('Cancelado')]);
    expect(within(screen.getByRole('main')).getByRole('link', { name: 'Pedir traslado' })).toHaveAttribute('href', '/pedir');
  });

  it('el menú de la cuenta lleva a «Mis viajes» y a «Mi cuenta»', async () => {
    montar('/mis-viajes');
    await userEvent.click(await screen.findByRole('button', { name: /menú de la cuenta/ }));
    const menu = screen.getByRole('dialog', { name: 'Tu cuenta' });
    expect(within(menu).getByRole('link', { name: 'Mis viajes' })).toHaveAttribute('href', '/mis-viajes');
    expect(within(menu).getByRole('link', { name: 'Mi cuenta' })).toHaveAttribute('href', '/mis-reservas');
  });

  it('otros roles van a su vista', async () => {
    const { router } = montarPanel('/mis-viajes');
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});

describe('HU-44 · cancelar (RN-09)', () => {
  it('sin conductor: confirma con motivo y queda cancelado', async () => {
    const { cancelaciones } = montar('/mis-viajes/20481');
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar viaje' }));
    const dialogo = screen.getByRole('dialog', { name: '¿Cancelar este viaje?' });
    expect(within(dialogo).getByText(/Reserva 20481/)).toBeInTheDocument();
    expect(within(dialogo).getByRole('radio', { name: 'Cambié de planes' })).toBeChecked();
    await userEvent.click(within(dialogo).getByRole('radio', { name: 'Mi vuelo se canceló' }));
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Sí, cancelar viaje' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(cancelaciones).toEqual([{ motivo: 'VUELO_CANCELADO' }]);
  });

  it('volver o Esc no cancela', async () => {
    const { cancelaciones } = montar('/mis-viajes/20481');
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar viaje' }));
    await userEvent.click(screen.getByRole('button', { name: 'Volver' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar viaje' }));
    await userEvent.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(cancelaciones).toEqual([]);
  });

  it('si el conductor ya aceptó (409) o falla, lo explica', async () => {
    montar('/mis-viajes/20481', { cancelar: [() => json(409, { code: 'con_conductor' }), () => json(500, {})] });
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar viaje' }));
    await userEvent.click(screen.getByRole('button', { name: 'Sí, cancelar viaje' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('para cancelar, contacta a la central');
    await userEvent.click(screen.getByRole('button', { name: 'Sí, cancelar viaje' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('No se pudo cancelar'));
  });

  it('con conductor no hay botón: «Para cancelar, contacta a la central»', async () => {
    montar('/mis-viajes/20481', { detalle: { ...VIAJE, estado: 'EN_CAMINO', cancelable: false } });
    expect(await screen.findByText('Para cancelar, contacta a la central.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar viaje' })).not.toBeInTheDocument();
  });
});
