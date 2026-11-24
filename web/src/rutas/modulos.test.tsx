/** HU-75 (DC-79): el menú y las rutas del despachador siguen sus módulos. */

import { screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import type { Modulo } from '../api/auth';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';

function conModulos(modulos: Modulo[]) {
  const servidor = new ServidorAuthFalso();
  servidor.modulos.set(2, modulos);
  return servidor;
}

describe('módulos del despachador', () => {
  it('el menú muestra Inicio y solo los módulos activos; Usuarios nunca', async () => {
    montarPanel('/', { servidor: conModulos(['MAPA', 'REPORTES']) });
    const menu = await screen.findByRole('navigation', {
      name: 'Menú principal',
    });
    expect(
      within(menu).getByRole('link', { name: 'Inicio' }),
    ).toBeInTheDocument();
    expect(
      within(menu).getByRole('link', { name: 'Mapa' }),
    ).toBeInTheDocument();
    expect(
      within(menu).getByRole('link', { name: 'Reportes' }),
    ).toBeInTheDocument();
    for (const nombre of [
      'Reservas',
      'Chat',
      'Convenios',
      'Vehículos',
      'Usuarios',
    ]) {
      expect(
        within(menu).queryByRole('link', { name: nombre }),
      ).not.toBeInTheDocument();
    }
  });

  it('por URL a un módulo apagado vuelve a Inicio con un aviso, sin consultar la API', async () => {
    const { servidor, router } = montarPanel('/reservas', {
      servidor: conModulos(['MAPA']),
    });
    expect(
      await screen.findByText(
        'No tienes acceso a este módulo. Pídeselo al administrador.',
      ),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/');
    expect(servidor.urls.some((u) => u.includes('/api/viajes/'))).toBe(false);
  });

  it('un módulo de administrador que se le activó queda disponible', async () => {
    montarPanel('/reportes', { servidor: conModulos(['REPORTES']) });
    expect(
      await screen.findByRole('heading', { level: 1, name: /Reportes/ }),
    ).toBeInTheDocument();
  });

  it('sin Reservas, Inicio no ofrece «Nueva reserva» ni los atajos', async () => {
    montarPanel('/', { servidor: conModulos(['MAPA']) });
    await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(
      screen.queryByRole('link', { name: 'Nueva reserva' }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole('list', { name: 'Atajos a las reservas' }),
    ).not.toBeInTheDocument();
  });
});
