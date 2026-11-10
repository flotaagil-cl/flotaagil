/** HU-31: cierre de caja en el panel (CP-36). */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorCajaFalso } from '../pruebas/servidorCajaFalso';

const ADMIN = 'admin@andes.example';

function montar(ruta = '/caja', email = ADMIN) {
  const contexto = montarPanel(ruta, { email });
  const caja = new ServidorCajaFalso(contexto.servidor);
  return { ...contexto, caja };
}

async function abrirDialogo() {
  const tabla = await screen.findByRole('table', { name: 'Turnos por cerrar' });
  await userEvent.click(within(tabla).getByRole('button', { name: 'Cerrar caja…' }));
  return screen.getByRole('dialog', { name: /Cerrar la caja del turno de Ana Conductora/ });
}

describe('permisos', () => {
  it('el administrador lo ve en el menú', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Cierre de caja' })).toBeInTheDocument();
  });

  it('el despachador no, y por URL ve «sin permiso» sin consultar la API', async () => {
    const { servidor } = montar('/caja', 'despacho@andes.example');
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes('/api/turnos/'))).toBe(false);
  });
});

describe('listado', () => {
  it('muestra el turno con su efectivo registrado', async () => {
    montar();
    const tabla = await screen.findByRole('table', { name: 'Turnos por cerrar' });
    const fila = within(tabla).getByText('Ana Conductora').closest('tr')!;
    expect(within(fila).getByText('ABCD12')).toBeInTheDocument();
    expect(within(fila).getByText('$48.000')).toBeInTheDocument();
  });

  it('con un viaje en ejecución no ofrece cerrar', async () => {
    const { caja } = montar();
    caja.turnos = [{ ...caja.turnos[0], con_viaje_en_ejecucion: true }];
    expect(await screen.findByText('Tiene un viaje en ejecución')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cerrar caja…' })).not.toBeInTheDocument();
  });

  it('sin turnos pendientes lo dice', async () => {
    const { caja } = montar();
    caja.turnos = [];
    expect(await screen.findByText('No hay turnos terminados por cerrar.')).toBeInTheDocument();
  });
});

describe('cierre (CP-36)', () => {
  it('rinde 48.000: cuadra y se cierra sin observación', async () => {
    const { caja } = montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByLabelText('Efectivo rendido (CLP)'), '48000');
    expect(within(dialogo).getByText('Cuadra con lo registrado.')).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar caja' }));
    expect(await screen.findByText(/Caja cerrada para Ana Conductora: cuadra con lo registrado/)).toBeInTheDocument();
    expect(caja.cierres).toEqual([{ id: 7, cuerpo: { monto_rendido: 48000 } }]);
    expect(await screen.findByText('No hay turnos terminados por cerrar.')).toBeInTheDocument();
  });

  it('rinde 45.000: pide la observación antes de enviar', async () => {
    const { caja } = montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByLabelText('Efectivo rendido (CLP)'), '45000');
    expect(within(dialogo).getByText('Faltan $3.000.')).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar caja' }));
    expect(within(dialogo).getByText('Explica la diferencia entre lo rendido y lo registrado.')).toBeInTheDocument();
    expect(caja.cierres).toEqual([]);
    await userEvent.type(within(dialogo).getByLabelText('Observación'), 'Vuelto mal dado');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar caja' }));
    expect(await screen.findByText(/faltaron \$3\.000/)).toBeInTheDocument();
    expect(caja.cierres[0].cuerpo).toEqual({ monto_rendido: 45000, observacion: 'Vuelto mal dado' });
  });

  it('rinde 0: falta todo', async () => {
    montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByLabelText('Efectivo rendido (CLP)'), '0');
    expect(within(dialogo).getByText('Faltan $48.000.')).toBeInTheDocument();
  });

  it('monto inválido', async () => {
    const { caja } = montar();
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByLabelText('Efectivo rendido (CLP)'), '-5');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar caja' }));
    expect(within(dialogo).getByText('Ingresa el efectivo rendido, en pesos enteros.')).toBeInTheDocument();
    expect(caja.cierres).toEqual([]);
  });

  it('segundo cierre: muestra el 409 del servidor', async () => {
    const { caja } = montar();
    caja.siguiente({ estado: 409, cuerpo: { detail: 'Este turno ya tiene su cierre de caja.', code: 'cierre_repetido' } });
    const dialogo = await abrirDialogo();
    await userEvent.type(within(dialogo).getByLabelText('Efectivo rendido (CLP)'), '48000');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar caja' }));
    expect(await within(dialogo).findByRole('alert')).toHaveTextContent('Este turno ya tiene su cierre de caja.');
  });
});
