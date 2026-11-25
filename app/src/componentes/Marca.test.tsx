// @vitest-environment jsdom
/** CC-27 (HU-80): el encabezado de la app muestra el logo de la empresa o, sin él, la marca de FlotaÁgil. */
import { act, cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { temaApp } from '../tema/instancia';
import { VueloDelViaje } from '../pantallas/VueloDelViaje';
import { Marca } from './Marca';

afterEach(cleanup);

describe('Marca', () => {
  it('sin logo muestra la marca de FlotaÁgil y cambia cuando llega el de la empresa', async () => {
    const { container } = render(<Marca clase="barra-logo" tamano={20} />);
    expect(screen.queryByRole('img')).toBeNull();
    expect(container.querySelector('.barra-logo svg')).not.toBeNull();

    // Mismo logo ya guardado: no se descarga nada.
    await act(() => temaApp.actualizar({ paleta: 'indigo', logo: null }, 'Andes Demo'));
    expect(document.body.dataset.paleta).toBe('indigo');
    expect(screen.queryByRole('img')).toBeNull();
  });
});

describe('Marca con iniciales (CC-21, CP-76)', () => {
  it('sin logo muestra las iniciales con el nombre de marca como texto alternativo', async () => {
    render(<Marca clase="login-logo" tamano={34} />);
    await act(() => temaApp.actualizar({ paleta: 'tiffany', logo: null, nombre_marca: 'Andes', iniciales: 'TA' }, 'Andes Demo SpA'));
    expect(screen.getByRole('img', { name: 'Iniciales de Andes' }).textContent).toBe('TA');
  });
});

describe('estado del vuelo', () => {
  it('lleva ícono y texto, no solo color', () => {
    render(<VueloDelViaje vuelo={{ numero: 'LA845', hora_programada: '2026-11-25T18:00:00Z', hora_estimada: null, estado_vuelo: 'CANCELADO' }} />);
    expect(screen.getByText(/cancelado por la aerolínea/).querySelector('svg')).not.toBeNull();
  });
});
