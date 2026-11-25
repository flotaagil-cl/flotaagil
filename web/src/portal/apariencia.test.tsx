/** CC-27 (HU-79, CP-73): el portal carga con la marca de la empresa, sin pintar antes los colores predeterminados. */

import { act, render, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Insignia } from '../diseno/Tarjeta';
import { jsonPortal, montarPortal } from '../pruebas/montarPortal';
import { guardar, leerGuardada } from '../diseno/aparienciaPublica';

const LOGO = {
  panel: '/api/publico/apariencia/transportes-andes/logo/v1/panel.png',
  portal: '/api/publico/apariencia/transportes-andes/logo/v1/portal.png',
  app: '/api/publico/apariencia/transportes-andes/logo/v1/app.png',
  correo: '/api/publico/apariencia/transportes-andes/logo/v1/correo.png',
  icono: '/api/publico/apariencia/transportes-andes/logo/v1/icono.png',
};
const RUTA = 'GET /api/publico/apariencia/transportes-andes/';
const marco = () => document.querySelector<HTMLElement>('.tema-portal');

describe.each([
  ['formulario público sin cuenta', '/solicitar/transportes-andes', false],
  ['ingreso del portal', '/solicitar/transportes-andes/ingresar', true],
  ['solicitud de convenio', '/solicitar/transportes-andes/convenio', false],
])('%s', (_pantalla, ruta, modulo) => {
  it('no pinta nada con tema antes de conocer la paleta y luego usa la de la empresa con su logo', async () => {
    let soltar: () => void = () => undefined;
    const espera = new Promise<void>((listo) => (soltar = listo));
    montarPortal(ruta, {
      modulo,
      responder: async (_peticion, camino) => {
        if (camino !== RUTA) return undefined;
        await espera;
        return jsonPortal(200, { paleta: 'indigo', logo: LOGO, nombre_marca: '', iniciales: '' });
      },
    });
    expect(await screen.findByRole('status', { name: 'Cargando' })).toBeInTheDocument();
    expect(marco()).toBeNull(); // ni un instante con Tiffany
    await act(async () => soltar());
    await waitFor(() => expect(marco()).toHaveAttribute('data-paleta', 'indigo'));
    const barra = await screen.findByRole('banner');
    await waitFor(() => expect(within(barra).getByRole('img', { name: /^Logo de/ })).toHaveAttribute('src', LOGO.portal));
  });
});

describe('respaldos', () => {
  it('sin logo propio muestra el de FlotaÁgil', async () => {
    montarPortal('/solicitar/transportes-andes', {
      responder: (_p, camino) => (camino === RUTA ? jsonPortal(200, { paleta: 'tiffany', logo: null, nombre_marca: '', iniciales: '' }) : undefined),
    });
    const barra = await screen.findByRole('banner');
    expect(within(barra).queryByRole('img', { name: /^Logo de/ })).not.toBeInTheDocument();
    expect(barra.querySelector('svg')).not.toBeNull();
  });

  it('CC-21: muestra el nombre de marca en el encabezado y, sin logo, las iniciales', async () => {
    montarPortal('/solicitar/transportes-andes', {
      responder: (_p, camino) => (camino === RUTA ? jsonPortal(200, { paleta: 'cian', logo: null, nombre_marca: 'Andes Traslados', iniciales: 'AT' }) : undefined),
    });
    const barra = await screen.findByRole('banner');
    expect(await within(barra).findByText('Andes Traslados')).toBeInTheDocument();
    expect(within(barra).getByRole('img', { name: 'Iniciales de Andes Traslados' })).toHaveTextContent('AT');
    expect(barra).not.toHaveTextContent('Transportes Andes Demo SpA');
  });

  it('si la apariencia no responde, el portal carga igual con la predeterminada', async () => {
    montarPortal('/solicitar/transportes-andes', {
      responder: (_p, camino) => (camino === RUTA ? jsonPortal(500, { detail: 'x' }) : undefined),
    });
    expect(await screen.findByRole('banner')).toBeInTheDocument();
    expect(marco()).not.toHaveAttribute('data-paleta');
  });

  it('lo guardado en el navegador se lee solo si sirve', () => {
    const datos = new Map<string, string>();
    const almacen = { getItem: (c: string) => datos.get(c) ?? null, setItem: (c: string, v: string) => void datos.set(c, v), removeItem: () => undefined };
    expect(leerGuardada(almacen, 'x')).toBeNull();
    guardar(almacen, 'x', { paleta: 'cian', logo: null, nombre_marca: '', iniciales: '' });
    expect(leerGuardada(almacen, 'x')).toEqual({ paleta: 'cian', logo: null, nombre_marca: '', iniciales: '' });
    datos.set('flotaagil.apariencia.x', 'no es json');
    expect(leerGuardada(almacen, 'x')).toBeNull();
    const roto = { getItem: () => { throw new Error('bloqueado'); }, setItem: () => { throw new Error('lleno'); }, removeItem: () => undefined };
    expect(leerGuardada(roto, 'x')).toBeNull();
    expect(() => guardar(roto, 'x', { paleta: 'cian', logo: null, nombre_marca: '', iniciales: '' })).not.toThrow();
  });
});

describe('estados', () => {
  it.each(['info', 'ok', 'revision', 'peligro', 'neutra'] as const)('la insignia %s lleva ícono y texto, no solo color', (tono) => {
    render(<Insignia tono={tono}>Estado</Insignia>);
    expect(screen.getByText('Estado').querySelector('svg')).not.toBeNull();
  });
});
