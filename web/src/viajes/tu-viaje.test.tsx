/** HU-43: «Tu viaje» del pasajero. */

import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { pasosDelViaje, textoDeCancelacion, type TuViaje } from './viaje';

const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

export const VIAJE: TuViaje = {
  id: 20481,
  estado: 'SOLICITADO',
  estado_texto: 'Solicitado',
  sentido: 'DESDE_AEROPUERTO',
  origen_dir: 'Aeropuerto de Santiago (SCL)',
  destino_dir: 'Hotel Cumbres, Vitacura',
  origen: { lat: -33.393, lng: -70.794 },
  destino: { lat: -33.39, lng: -70.58 },
  recogida_en: '2026-11-13T21:40:00Z',
  pasajeros: 1,
  maletas: 2,
  vuelo_salida_en: null,
  vuelo_salida_tipo: null,
  creado_en: '2026-11-12T00:14:00Z',
  cancelable: true,
  conductor: null,
  vehiculo: null,
  vuelo: null,
  pasos: [{ estado: 'SOLICITADO', creado_en: '2026-11-12T00:14:00Z' }],
};

const conConductor = (cambios: Partial<TuViaje> = {}): TuViaje => ({
  ...VIAJE,
  estado: 'EN_CAMINO',
  cancelable: false,
  conductor: { nombre: 'Juan Rojas' },
  vehiculo: { marca_modelo: 'Toyota Corolla', patente: 'KTRS42' },
  vuelo: { numero: 'LA 845', hora_programada: '2026-11-13T21:20:00Z', hora_estimada: '2026-11-13T21:45:00Z', estado_vuelo: 'DEMORADO' },
  pasos: [
    { estado: 'SOLICITADO', creado_en: '2026-11-12T00:14:00Z' },
    { estado: 'ASIGNADO', creado_en: '2026-11-13T20:00:00Z' },
    { estado: 'ACEPTADO', creado_en: '2026-11-13T20:01:00Z' },
    { estado: 'EN_CAMINO', creado_en: '2026-11-13T20:30:00Z' },
  ],
  ...cambios,
});

export function montarViaje(ruta: string, respuesta: () => Response) {
  const servidor = new ServidorAuthFalso();
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    if (new URL(peticion.url).pathname.startsWith('/api/mi-cuenta/reservas/')) return respuesta();
    return original(peticion);
  };
  return montarPanel(ruta, { email: 'pasajero@andes.example', servidor });
}

describe('HU-43 · avance del viaje', () => {
  it('sin conductor: pedido recibido y buscando conductor', () => {
    const pasos = pasosDelViaje(VIAJE);
    expect(pasos.map((p) => p.estado)).toEqual(['hecho', 'actual', 'pendiente', 'pendiente', 'pendiente', 'pendiente']);
    expect(pasos[1]).toMatchObject({ titulo: 'Conductor asignado', detalle: 'Buscando tu conductor' });
    expect(pasos[3].titulo).toBe('Esperándote en salida');
  });

  it('en camino: el conductor aparece en su paso; en la ciudad los textos cambian', () => {
    const pasos = pasosDelViaje(conConductor());
    expect(pasos.map((p) => p.estado)).toEqual(['hecho', 'hecho', 'actual', 'pendiente', 'pendiente', 'pendiente']);
    expect(pasos[1].detalle).toBe('Juan Rojas');
    expect(pasos[2]).toMatchObject({ titulo: 'En camino al aeropuerto', detalle: 'vie 13-11-2026 17:30' });
    const ciudad = pasosDelViaje({ ...VIAJE, sentido: 'URBANO', estado: 'FINALIZADO' });
    expect(ciudad.every((p) => p.estado === 'hecho')).toBe(true);
    expect(ciudad[2].titulo).toBe('En camino a buscarte');
    expect(ciudad[3].titulo).toBe('Te espera en el punto de recogida');
  });

  it('asignado sin aceptar sigue buscando; pendiente de confirmar pide responder el WhatsApp', () => {
    expect(pasosDelViaje({ ...VIAJE, estado: 'ASIGNADO' })[1].estado).toBe('actual');
    expect(pasosDelViaje({ ...VIAJE, estado: 'ACEPTADO', conductor: { nombre: 'Juan Rojas' } })[1]).toMatchObject({ estado: 'actual', detalle: 'Juan Rojas' });
    const pendiente = pasosDelViaje({ ...VIAJE, estado: 'PENDIENTE_CONFIRMACION' });
    expect(pendiente[0]).toMatchObject({ estado: 'actual', detalle: 'Confírmalo respondiendo el WhatsApp' });
  });

  it('texto para cancelar: solo donde no se puede cancelar desde la cuenta (RN-09)', () => {
    expect(textoDeCancelacion({ estado: 'SOLICITADO', cancelable: true })).toBeNull();
    expect(textoDeCancelacion({ estado: 'EN_CAMINO', cancelable: false })).toBe('Para cancelar, contacta a la central.');
    expect(textoDeCancelacion({ estado: 'FINALIZADO', cancelable: false })).toBeNull();
    expect(textoDeCancelacion({ estado: 'CANCELADO', cancelable: false })).toBeNull();
  });
});

describe('HU-43 · pantalla «Tu viaje»', () => {
  it('sin conductor todavía: lo dice y no muestra datos del conductor', async () => {
    montarViaje('/mis-viajes/20481', () => json(200, VIAJE));
    expect(await screen.findByRole('heading', { name: 'Tu viaje' })).toBeInTheDocument();
    expect(screen.getByText('Buscando conductor')).toBeInTheDocument();
    expect(screen.getByText(/Reserva 20481 · Desde el aeropuerto/)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Estamos buscando tu conductor' })).toBeInTheDocument();
    expect(screen.queryByText(/Para cancelar, contacta a la central/)).not.toBeInTheDocument();
  });

  it('con conductor: nombre, vehículo, patente, vuelo y avance; sin cancelar desde la cuenta', async () => {
    montarViaje('/mis-viajes/20481', () => json(200, conConductor()));
    const conductor = await screen.findByRole('region', { name: 'Juan Rojas' });
    expect(within(conductor).getByText('Toyota Corolla')).toBeInTheDocument();
    expect(within(conductor).getByLabelText('Patente KTRS42')).toBeInTheDocument();
    expect(screen.getByText('Conductor en camino')).toBeInTheDocument();
    const vuelo = screen.getByRole('region', { name: 'Vuelo LA 845' });
    expect(within(vuelo).getByText('Atrasado')).toBeInTheDocument();
    expect(within(vuelo).getByText(/Llega vie 13-11-2026 18:45/)).toBeInTheDocument();
    const avance = screen.getByRole('list', { name: 'Avance de tu viaje' });
    expect(within(avance).getAllByRole('listitem')[2]).toHaveAttribute('aria-current', 'step');
    expect(screen.getByText('Para cancelar, contacta a la central.')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Mapa de tu viaje' })).toBeInTheDocument();
  });

  it('cancelado: lo informa sin avance', async () => {
    montarViaje('/mis-viajes/20481', () => json(200, { ...VIAJE, estado: 'CANCELADO', cancelable: false }));
    expect(await screen.findByText('Este viaje fue cancelado.')).toBeInTheDocument();
    expect(screen.queryByRole('list', { name: 'Avance de tu viaje' })).not.toBeInTheDocument();
  });

  it('un viaje ajeno (404) o un número inválido: «No encontramos este viaje»', async () => {
    montarViaje('/mis-viajes/999', () => json(404, { detail: 'No encontrado.' }));
    expect(await screen.findByRole('heading', { name: 'No encontramos este viaje' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ver mis viajes' })).toHaveAttribute('href', '/mis-viajes');
  });

  it('número inválido y falla del servidor', async () => {
    montarViaje('/mis-viajes/abc', () => json(200, VIAJE));
    expect(await screen.findByRole('heading', { name: 'No encontramos este viaje' })).toBeInTheDocument();
  });

  it('falla del servidor', async () => {
    montarViaje('/mis-viajes/20481', () => json(500, {}));
    expect(await screen.findByText('No pudimos cargar tu viaje. Recarga la página.')).toBeInTheDocument();
  });

  it('otros roles van a su vista', async () => {
    const { router } = montarPanel('/mis-viajes/20481');
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});
