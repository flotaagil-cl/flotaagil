/** HU-53 (CC-22): solicitud pública de convenio, sin cuenta. */

import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { jsonPortal, montarPortal } from '../pruebas/montarPortal';

const RUTA = '/solicitar/transportes-andes/convenio';

describe('HU-53 · solicitud pública de convenio', () => {
  it('envía los datos con los correos autorizados y confirma la recepción', async () => {
    const { peticiones } = montarPortal(RUTA, {
      responder: (_p, ruta) => (ruta.endsWith('/convenio/') ? jsonPortal(201, { mensaje: 'ok' }) : undefined),
    });
    await userEvent.type(await screen.findByLabelText('Razón social'), 'Minera Sintética S.A.');
    await userEvent.type(screen.getByLabelText('RUT de la empresa'), '76543210-3');
    await userEvent.type(screen.getByLabelText('Dirección'), 'Av. Apoquindo 3000');
    await userEvent.type(screen.getByLabelText('Persona de contacto'), 'Ana Contacto');
    await userEvent.type(screen.getByLabelText('Correo de contacto'), 'ana@minera.example');
    await userEvent.type(screen.getByLabelText('Teléfono de contacto'), '+56900009601');
    await userEvent.type(screen.getByLabelText('Viajes estimados al mes'), '40');
    await userEvent.type(screen.getByLabelText('Correos autorizados para pedir viajes'), '@minera.example, pedro@otra.example');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByRole('heading', { name: 'Solicitud recibida' })).toBeInTheDocument();
    expect(peticiones[0].cuerpo).toMatchObject({
      cliente_rut: '76543210-3',
      viajes_estimados_mes: 40,
      correos_autorizados: ['@minera.example', 'pedro@otra.example'],
      sitio_web: '',
    });
  });

  it('valida los campos y muestra el error del servidor', async () => {
    const { peticiones } = montarPortal(RUTA, {
      responder: (_p, ruta) => (ruta.endsWith('/convenio/') ? jsonPortal(400, { cliente_rut: ['RUT inválido.'] }) : undefined),
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Enviar solicitud' }));
    expect(screen.getByText('Completa «Razón social».')).toBeInTheDocument();
    expect(peticiones).toHaveLength(0);
    for (const [etiqueta, valor] of [
      ['Razón social', 'X'],
      ['RUT de la empresa', '1-1'],
      ['Dirección', 'Y'],
      ['Persona de contacto', 'Z'],
      ['Correo de contacto', 'z@x.example'],
      ['Teléfono de contacto', '+56900009601'],
      ['Viajes estimados al mes', '2'],
    ]) {
      await userEvent.type(screen.getByLabelText(etiqueta), valor);
    }
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByText('RUT inválido.')).toBeInTheDocument();
  });

  it('con el módulo de cuentas no está disponible (se usa el registro con cuenta)', async () => {
    montarPortal(RUTA, { modulo: true });
    expect(await screen.findByRole('heading', { name: /no está disponible/i })).toBeInTheDocument();
  });
});
