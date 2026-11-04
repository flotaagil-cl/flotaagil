// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MiTurno, type ResumenDelTurno } from './MiTurno';

const VIAJE = {
  id: 1,
  finalizado_en: '2026-11-04T15:30:00Z',
  origen: 'Plaza de Armas',
  destino: 'Providencia 1234',
  monto: 15000,
  metodo: 'EFECTIVO',
  cerrado_por_central: false,
} as const;

const resumen = (cambios: Partial<ResumenDelTurno> = {}): ResumenDelTurno => ({
  en_turno: true,
  inicio: '2026-11-04T12:00:00Z',
  fin: null,
  viajes: [VIAJE],
  totales: [{ metodo: 'EFECTIVO', viajes: 1, monto: 15000 }],
  total: 15000,
  ...cambios,
});

afterEach(cleanup);

describe('Mi turno (HU-18)', () => {
  it('muestra hora, origen, destino, monto y método de cada viaje', async () => {
    render(<MiTurno cargar={async () => resumen()} volver={() => {}} />);
    const tarjeta = (await screen.findByRole('heading', { name: '04-11 12:30' })).parentElement!;
    expect(within(tarjeta).getByText('Plaza de Armas')).toBeTruthy();
    expect(within(tarjeta).getByText('Providencia 1234')).toBeTruthy();
    expect(within(tarjeta).getByText('$15.000')).toBeTruthy();
    expect(within(tarjeta).getByText('Efectivo')).toBeTruthy();
    expect(within(tarjeta).queryByText('Cerrado por la central')).toBeNull();
    expect(screen.getByText('Turno en curso desde 04-11 09:00.')).toBeTruthy();
  });

  it('marca los cerrados por la central', async () => {
    render(<MiTurno cargar={async () => resumen({ viajes: [{ ...VIAJE, cerrado_por_central: true }] })} volver={() => {}} />);
    expect(await screen.findByText('Cerrado por la central')).toBeTruthy();
  });

  it('suma por método de pago y en total', async () => {
    const datos = resumen({
      viajes: [VIAJE, { ...VIAJE, id: 2, metodo: 'TARJETA', monto: 7000 }],
      totales: [
        { metodo: 'EFECTIVO', viajes: 1, monto: 15000 },
        { metodo: 'TARJETA', viajes: 1, monto: 7000 },
      ],
      total: 22000,
    });
    render(<MiTurno cargar={async () => datos} volver={() => {}} />);
    const totales = (await screen.findByRole('heading', { name: 'Totales por método de pago' })).parentElement!;
    expect(within(totales).getByText('Efectivo (1)')).toBeTruthy();
    expect(within(totales).getByText('Tarjeta (1)')).toBeTruthy();
    expect(within(totales).getByText('$22.000')).toBeTruthy();
  });

  it('fuera de turno rotula el último turno', async () => {
    render(<MiTurno cargar={async () => resumen({ en_turno: false, fin: '2026-11-04T20:00:00Z' })} volver={() => {}} />);
    expect(await screen.findByText('Último turno: 04-11 09:00 a 04-11 17:00.')).toBeTruthy();
  });

  it('turno sin viajes, sin totales', async () => {
    render(<MiTurno cargar={async () => resumen({ viajes: [], totales: [], total: 0 })} volver={() => {}} />);
    expect(await screen.findByText('Sin viajes completados en este turno.')).toBeTruthy();
    expect(screen.queryByRole('heading', { name: 'Totales por método de pago' })).toBeNull();
  });

  it('nunca ha tenido un turno', async () => {
    render(<MiTurno cargar={async () => resumen({ en_turno: false, inicio: null, viajes: [], totales: [], total: 0 })} volver={() => {}} />);
    expect(await screen.findByText('Aún no tienes turnos registrados.')).toBeTruthy();
    expect(screen.queryByText('Sin viajes completados en este turno.')).toBeNull();
  });

  it('si falla lo dice, y Actualizar lo reintenta', async () => {
    const cargar = vi.fn<() => Promise<ResumenDelTurno>>().mockRejectedValueOnce(new Error('sin red')).mockResolvedValue(resumen());
    render(<MiTurno cargar={cargar} volver={() => {}} />);
    expect((await screen.findByRole('alert')).textContent).toBe('No se pudieron cargar tus viajes.');
    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }));
    expect(await screen.findByText('Plaza de Armas')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('Volver regresa al inicio', async () => {
    const volver = vi.fn();
    render(<MiTurno cargar={async () => resumen()} volver={volver} />);
    await screen.findByText('Plaza de Armas');
    fireEvent.click(screen.getByRole('button', { name: 'Volver' }));
    expect(volver).toHaveBeenCalledOnce();
  });
});
