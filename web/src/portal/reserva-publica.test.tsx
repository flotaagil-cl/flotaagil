/** HU-51 (CC-22): reserva pública sin cuenta y su confirmación por correo. CP-47 y CP-48. */

import { fireEvent, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonPortal, montarPortal } from '../pruebas/montarPortal';

const RESPUESTA = {
  id: 501,
  estado: 'PENDIENTE_CONFIRMACION',
  recogida_en: '2026-11-20T13:00:00Z',
  confirmar_hasta: '2026-11-19T13:00:00Z',
  mensaje: 'Te enviamos un correo.',
};

async function llenarViaje() {
  await userEvent.type(await screen.findByLabelText('Origen'), 'Av. Providencia 1208');
  await userEvent.type(screen.getByLabelText('Destino'), 'Plaza de Armas');
  await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
}

describe('HU-51 · reserva pública', () => {
  it('pide el viaje, luego los datos de contacto, y avisa que revise el correo', async () => {
    // CC-23 (DC-77): la casilla de RUT (HU-54) queda solo con el módulo de cuentas.
    const { peticiones } = montarPortal('/solicitar/transportes-andes/reservar', {
      modulo: true,
      responder: (_p, ruta) => (ruta === 'POST /api/portal/transportes-andes/reservas/' ? jsonPortal(201, RESPUESTA) : undefined),
    });
    await llenarViaje();
    expect(await screen.findByRole('heading', { name: 'Tus datos' })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Nombre y apellido'), 'Paula Pasajera');
    await userEvent.type(screen.getByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Teléfono de contacto'), '+56900009401');
    await userEvent.click(screen.getByRole('checkbox', { name: '¿Es una empresa?' }));
    await userEvent.type(screen.getByLabelText('Razón social'), 'Minera Sintética S.A.');
    await userEvent.type(screen.getByLabelText('RUT de la empresa'), '76543210-3');
    await userEvent.type(screen.getByLabelText('Persona de contacto'), 'Ana Contacto');
    await userEvent.click(screen.getByRole('checkbox', { name: /aviso de privacidad/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByRole('heading', { name: 'Revisa tu correo' })).toBeInTheDocument();
    expect(peticiones[0].cuerpo).toMatchObject({
      origen_dir: 'Av. Providencia 1208',
      correo: 'paula@correo.example',
      es_empresa: true,
      empresa_rut: '76543210-3',
      acepta_privacidad: true,
      sitio_web: '',
    });
  });

  it('sin cuenta, la nota no habla de «Mis viajes» ni de un aviso ya aceptado', async () => {
    montarPortal('/solicitar/transportes-andes');
    await screen.findByLabelText('Origen');
    expect(screen.getByText(/Te enviaremos un enlace por correo para confirmar tu reserva/)).toBeInTheDocument();
    expect(screen.queryByText(/Mis viajes/)).not.toBeInTheDocument();
    expect(screen.queryByText(/al crear tu cuenta/)).not.toBeInTheDocument();
  });

  it('no envía sin correo ni privacidad, y muestra los errores del servidor', async () => {
    const { peticiones } = montarPortal('/solicitar/transportes-andes', {
      responder: (_p, ruta) => (ruta.endsWith('/reservas/') ? jsonPortal(400, { telefono: ['Teléfono inválido.'] }) : undefined),
    });
    await llenarViaje();
    await userEvent.type(await screen.findByLabelText('Nombre y apellido'), 'Paula');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(screen.getByText(/Escribe un correo válido/)).toBeInTheDocument();
    expect(screen.getByText('Debes aceptar el aviso de privacidad.')).toBeInTheDocument();
    expect(peticiones).toHaveLength(0);
    await userEvent.type(screen.getByLabelText('Correo'), 'paula@correo.example');
    await userEvent.type(screen.getByLabelText('Teléfono de contacto'), '12');
    fireEvent.click(screen.getByRole('checkbox', { name: /aviso de privacidad/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByText('Teléfono inválido.')).toBeInTheDocument();
  });

  it.each([
    [200, 'Reserva confirmada'],
    [409, 'Esta reserva ya no está pendiente'],
    [410, 'El plazo para confirmar venció'],
    [400, 'El enlace no es válido'],
  ])('el enlace del correo responde %i: «%s»', async (estado, titulo) => {
    const cuerpo =
      estado === 200
        ? { id: 501, estado: 'SOLICITADO', recogida_en: RESPUESTA.recogida_en, origen_dir: 'Origen', destino_dir: 'Destino' }
        : { detail: 'x' };
    const { peticiones } = montarPortal('/solicitar/transportes-andes/confirmar/abc:firma', {
      responder: (_p, ruta) => (ruta.endsWith('/reservas/confirmar/') ? jsonPortal(estado, cuerpo) : undefined),
    });
    expect(await screen.findByRole('heading', { name: titulo })).toBeInTheDocument();
    await waitFor(() => expect(peticiones[0].cuerpo).toEqual({ token: 'abc:firma' }));
  });
});
