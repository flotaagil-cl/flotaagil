/** HU-50 (CC-22, DC-51): sin el módulo de cuentas, el portal no ofrece ingreso, cuenta ni registro. CP-46. */

import { screen, waitFor } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { montarPortal } from '../pruebas/montarPortal';

const montar = (ruta: string, modulo: boolean) => montarPortal(ruta, { modulo });

describe('HU-50 · módulo de cuentas en el portal', () => {
  it.each(['cuenta', 'activar', 'registro-empresa'])('sin el módulo, /%s no está disponible', async (pagina) => {
    montar(`/solicitar/transportes-andes/${pagina}`, false);
    expect(await screen.findByRole('heading', { name: /no está disponible/i })).toBeInTheDocument();
  });

  it('sin el módulo, ingresar lleva al portal de la empresa', async () => {
    const { router } = montar('/solicitar/transportes-andes/ingresar', false);
    await waitFor(() => expect(router.state.location.pathname).toBe('/solicitar/transportes-andes'));
  });

  it('con el módulo, crear cuenta sigue disponible', async () => {
    montar('/solicitar/transportes-andes/cuenta', true);
    expect(await screen.findByRole('heading', { name: /crea tu cuenta/i })).toBeInTheDocument();
  });

  it('con el módulo, la portada ofrece «Ingresar» y «Reservar sin cuenta» (HU-60)', async () => {
    montar('/solicitar/transportes-andes', true);
    expect(await screen.findByRole('heading', { name: 'Pide tu traslado' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ingresar' })).toHaveAttribute('href', '/solicitar/transportes-andes/ingresar');
    expect(screen.getByRole('link', { name: 'Reservar sin cuenta' })).toHaveAttribute('href', '/solicitar/transportes-andes/reservar');
  });

  it('«Reservar sin cuenta» muestra el formulario público', async () => {
    montar('/solicitar/transportes-andes/reservar', true);
    expect(await screen.findByRole('heading', { name: '¿A dónde te llevamos?' })).toBeInTheDocument();
  });
});
