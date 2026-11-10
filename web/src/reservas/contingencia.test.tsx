/** HU-32: reserva de contingencia en el panel y conciliación por folio en Reportes. */

import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { ServidorReportesFalso } from '../pruebas/servidorReportesFalso';

function instalar(auth: ServidorAuthFalso, respuesta?: Respuesta) {
  const anterior = auth.api;
  const cuerpos: Record<string, unknown>[] = [];
  auth.api = async (peticion: Request, url: URL): Promise<Respuesta> => {
    if (url.pathname === '/api/viajes/contingencia/conductores/') return { estado: 200, cuerpo: [{ id: 3, nombre: 'Ana Conductora' }] };
    if (url.pathname === '/api/viajes/contingencia/' && peticion.method === 'POST') {
      cuerpos.push((await peticion.json()) as Record<string, unknown>);
      return respuesta ?? { estado: 201, cuerpo: { id: 77, folio_contingencia: 'C-0001' } };
    }
    return anterior!(peticion, url);
  };
  return cuerpos;
}

function fecha(etiqueta: string, valor: string) {
  fireEvent.change(screen.getByLabelText(etiqueta), { target: { value: valor } });
}

async function llenarBase() {
  await userEvent.type(await screen.findByLabelText('Folio de la hoja'), 'C-0001');
  await userEvent.type(screen.getByLabelText('Nombre del pasajero'), 'Pasajera Sintética');
  await userEvent.type(screen.getByLabelText('Teléfono (WhatsApp)'), '+56900007001');
  await userEvent.type(screen.getByLabelText('Origen'), 'Av. Providencia 1234');
  await userEvent.type(screen.getByLabelText('Destino'), 'Plaza de Armas');
}

describe('reserva de contingencia', () => {
  it('el listado ofrece el formulario', async () => {
    montarPanel('/reservas');
    expect(await screen.findByRole('link', { name: 'Reserva de contingencia' })).toHaveAttribute('href', '/reservas/contingencia');
  });

  it('finalizado: envía horas reales, conductor, método y monto', async () => {
    const { servidor, router } = montarPanel('/reservas/contingencia');
    const cuerpos = instalar(servidor);
    await llenarBase();
    fecha('Recogida real', '2026-07-14T10:00');
    fecha('Término real', '2026-07-14T10:40');
    await userEvent.selectOptions(await screen.findByLabelText('Conductor'), 'Ana Conductora');
    await userEvent.type(screen.getByLabelText('Monto cobrado (CLP)'), '15000');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar reserva' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/reservas/77'));
    expect(cuerpos[0]).toMatchObject({
      folio: 'C-0001',
      resultado: 'FINALIZADO',
      conductor: 3,
      metodo: 'EFECTIVO',
      monto: 15000,
      recogida_en: '2026-07-14T14:00:00.000Z',
      termino_en: '2026-07-14T14:40:00.000Z',
    });
  });

  it('cancelado: pide motivo y no exige conductor', async () => {
    const { servidor } = montarPanel('/reservas/contingencia');
    const cuerpos = instalar(servidor);
    await llenarBase();
    await userEvent.click(screen.getByLabelText(/Cancelado/));
    fecha('Recogida real', '2026-07-14T10:00');
    fecha('Hora de la cancelación', '2026-07-14T09:30');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar reserva' }));
    expect(screen.getByText('Indica el motivo de la cancelación.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Motivo de la cancelación'), 'No llegó al punto');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar reserva' }));
    await waitFor(() => expect(cuerpos).toHaveLength(1));
    expect(cuerpos[0]).toMatchObject({ resultado: 'CANCELADO', motivo: 'No llegó al punto' });
    expect(cuerpos[0]).not.toHaveProperty('conductor');
  });

  it('valida antes de enviar', async () => {
    const { servidor } = montarPanel('/reservas/contingencia');
    const cuerpos = instalar(servidor);
    await userEvent.click(await screen.findByRole('button', { name: 'Ingresar reserva' }));
    expect(screen.getByText('Hasta 20 letras, números o guiones.')).toBeInTheDocument();
    expect(screen.getByText('Elige el conductor.')).toBeInTheDocument();
    expect(cuerpos).toEqual([]);
  });

  it('el error del servidor queda en su campo (folio repetido)', async () => {
    const { servidor } = montarPanel('/reservas/contingencia');
    instalar(servidor, { estado: 400, cuerpo: { folio: ['Ese folio ya fue ingresado en tu empresa.'] } });
    await llenarBase();
    fecha('Recogida real', '2026-07-14T10:00');
    fecha('Término real', '2026-07-14T10:40');
    await userEvent.selectOptions(await screen.findByLabelText('Conductor'), 'Ana Conductora');
    await userEvent.type(screen.getByLabelText('Monto cobrado (CLP)'), '15000');
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar reserva' }));
    expect(await screen.findByText('Ese folio ya fue ingresado en tu empresa.')).toBeInTheDocument();
  });
});

describe('conciliación por folio en Reportes', () => {
  it('muestra folios, montos y los viajes sin turno', async () => {
    const contexto = montarPanel('/reportes?tipo=contingencia', { email: 'admin@andes.example' });
    const reportes = new ServidorReportesFalso(contexto.servidor);
    reportes.reportes.contingencia = {
      columnas: [
        { clave: 'folio', titulo: 'Folio', tipo: 'texto' },
        { clave: 'turno', titulo: 'Turno', tipo: 'texto' },
        { clave: 'monto', titulo: 'Monto', tipo: 'pesos' },
      ],
      filas: [{ folio: 'C-0001', turno: 'Sin turno', monto: 15000 }],
      totales: { folio: 'Total, 1 folios', turno: '1 sin turno', monto: 15000 },
      count: 1,
      next: null,
      previous: null,
    };
    const tabla = await screen.findByRole('table', { name: 'Conciliación de contingencia' });
    expect(within(tabla).getByText('C-0001')).toBeInTheDocument();
    expect(within(tabla).getByText('1 sin turno')).toBeInTheDocument();
    expect(screen.getByText(/Reservas de contingencia por folio/)).toBeInTheDocument();
  });
});
