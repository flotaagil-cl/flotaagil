/** HU-06: reportes operativos y exportación CSV (CP-25). */

import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { hoy } from '../hora/hora';
import { montarPanel } from '../pruebas/montar';
import { LIQUIDACION, ServidorReportesFalso } from '../pruebas/servidorReportesFalso';

const ADMIN = 'admin@andes.example';

function montar(ruta = '/reportes', email = ADMIN) {
  const contexto = montarPanel(ruta, { email });
  const reportes = new ServidorReportesFalso(contexto.servidor);
  return { ...contexto, reportes };
}

const tabla = (nombre: string) => screen.findByRole('table', { name: nombre });

beforeEach(() => {
  vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() }));
});

describe('permisos', () => {
  it('el administrador lo ve en el menú', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Reportes' })).toBeInTheDocument();
  });

  it('el despachador no, y por URL ve «sin permiso» sin consultar la API', async () => {
    const { servidor } = montar('/reportes', 'despacho@andes.example');
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes('/api/reportes/'))).toBe(false);
  });
});

describe('liquidación', () => {
  it('por defecto muestra hoy, con los cierres forzados y los totales del período', async () => {
    const { reportes } = montar();
    const contenido = await tabla('Liquidación por conductor');
    const fila = within(contenido).getByText('Ana Conductora').closest('tr')!;
    expect(within(fila).getByText('15-07-2026')).toBeInTheDocument();
    expect(within(fila).getByText('$13.000')).toBeInTheDocument();
    expect(within(contenido).getByRole('columnheader', { name: 'Cierres forzados' })).toBeInTheDocument();
    const totales = within(contenido).getByText('Total', { selector: 'tfoot *' }).closest('tr')!;
    expect(within(totales).getByText('$13.000')).toBeInTheDocument();
    expect(reportes.consultas[0]).toBe(`liquidacion?desde=${hoy()}&hasta=${hoy()}`);
  });

  it('explica qué incluye', async () => {
    montar();
    expect(await screen.findByText(/Incluye los cierres forzados/)).toBeInTheDocument();
  });
});

describe('filtros', () => {
  it('por fecha, conductor y convenio, con opciones de la API', async () => {
    const { reportes } = montar();
    await tabla('Liquidación por conductor');
    const conductor = screen.getByRole('combobox', { name: 'Conductor' });
    await within(conductor).findByRole('option', { name: 'Ana Conductora' });
    await userEvent.selectOptions(conductor, 'Ana Conductora');
    await waitFor(() => expect(reportes.consultas.at(-1)).toContain('conductor=3'));
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Convenio' }), 'Minera Norte');
    await waitFor(() => expect(reportes.consultas.at(-1)).toContain('convenio=9'));
    fireEvent.change(screen.getByLabelText('Desde'), { target: { value: '2026-07-01' } });
    await waitFor(() => expect(reportes.consultas.at(-1)).toContain('desde=2026-07-01'));
  });

  it('una fecha inicial posterior a la final se explica, sin consultar', async () => {
    const { reportes } = montar('/reportes?desde=2026-07-31&hasta=2026-07-01');
    expect(await screen.findByText('La fecha inicial no puede ser posterior a la final.')).toBeInTheDocument();
    expect(reportes.consultas).toEqual([]);
    expect(screen.getByRole('button', { name: 'Exportar CSV' })).toBeDisabled();
  });

  it('los filtros quedan en la URL', async () => {
    const { reportes } = montar('/reportes?tipo=cancelaciones&desde=2026-07-01&hasta=2026-07-31');
    await tabla('Cancelaciones');
    expect(reportes.consultas[0]).toBe('cancelaciones?desde=2026-07-01&hasta=2026-07-31');
  });

  it('un tipo desconocido en la URL vuelve a la liquidación', async () => {
    montar('/reportes?tipo=otro');
    expect(await tabla('Liquidación por conductor')).toBeInTheDocument();
  });
});

describe('otros reportes', () => {
  it('cancelaciones: tasa por origen', async () => {
    montar();
    await tabla('Liquidación por conductor');
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Reporte' }), 'Cancelaciones');
    const contenido = await tabla('Cancelaciones');
    const fila = within(contenido).getByText('Pasajero').closest('tr')!;
    expect(within(fila).getByText('12,5 %')).toBeInTheDocument();
    expect(within(contenido).getByText('Total, de 16 reservas')).toBeInTheDocument();
  });

  it('al cambiar de reporte no muestra los datos del anterior bajo el título nuevo', async () => {
    const { reportes } = montar();
    await tabla('Liquidación por conductor');
    let soltar = () => {};
    reportes.espera = new Promise((resolver) => {
      soltar = resolver;
    });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Reporte' }), 'Facturación por convenio');
    expect(await screen.findByLabelText('Cargando el reporte')).toBeInTheDocument();
    expect(screen.queryByRole('table', { name: 'Facturación por convenio' })).not.toBeInTheDocument();
    soltar();
    expect(await screen.findByText('Sin datos en este período.')).toBeInTheDocument();
  });

  it('sin datos lo dice', async () => {
    montar('/reportes?tipo=facturacion');
    expect(await screen.findByText('Sin datos en este período.')).toBeInTheDocument();
  });

  it('muestra un valor vacío como guion', async () => {
    const { reportes } = montar();
    reportes.reportes.liquidacion = { ...LIQUIDACION, filas: [{ ...LIQUIDACION.filas[0], cierres_forzados: null }] };
    const contenido = await tabla('Liquidación por conductor');
    expect(within(contenido).getByText('—')).toBeInTheDocument();
  });

  it('pagina', async () => {
    const { reportes } = montar();
    reportes.reportes.liquidacion = { ...LIQUIDACION, next: 'x' };
    await tabla('Liquidación por conductor');
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
    await waitFor(() => expect(reportes.consultas.at(-1)).toContain('page=2'));
  });

  it('una falla ofrece reintentar', async () => {
    const { reportes } = montar();
    reportes.siguiente('/api/reportes/liquidacion/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await tabla('Liquidación por conductor')).toBeInTheDocument();
  });
});

describe('exportar CSV', () => {
  it('descarga con los mismos filtros', async () => {
    const clic = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    const { reportes } = montar('/reportes?desde=2026-07-01&hasta=2026-07-31&conductor=3');
    await tabla('Liquidación por conductor');
    await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }));
    await waitFor(() => expect(clic).toHaveBeenCalled());
    expect(reportes.descargas).toEqual(['liquidacion?desde=2026-07-01&hasta=2026-07-31&conductor=3']);
    expect((clic.mock.contexts[0] as HTMLAnchorElement).download).toBe('liquidacion-2026-07-01-2026-07-31.csv');
    expect(URL.revokeObjectURL).toHaveBeenCalled();
  });

  it('una falla se informa', async () => {
    const { reportes } = montar();
    reportes.siguiente('/api/reportes/liquidacion/csv/', { estado: 500, cuerpo: {} });
    await tabla('Liquidación por conductor');
    await userEvent.click(screen.getByRole('button', { name: 'Exportar CSV' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
