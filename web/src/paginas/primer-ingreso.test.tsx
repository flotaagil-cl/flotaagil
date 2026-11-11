/** DC-40: primer ingreso con contraseña temporal para todos los roles web. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { crearRutas } from '../rutas/tabla';

function montar(ruta = '/login') {
  const servidor = new ServidorAuthFalso();
  const { entorno } = crearEntorno({ servidor, locks: crearLocks() });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { servidor, router };
}

async function entrar(email: string, password: string) {
  await userEvent.type(await screen.findByLabelText('Correo'), email);
  await userEvent.type(screen.getByLabelText('Contraseña'), password);
  await userEvent.click(screen.getByRole('button', { name: /Ingresar|Entrar/ }));
}

describe('primer ingreso', () => {
  it('con temporal lleva a crear la contraseña y luego a su vista', async () => {
    const { router } = montar();
    await entrar('temporal@andes.example', 'Temporal123');
    expect(await screen.findByRole('heading', { name: /Crea tu contraseña/ })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/primer-ingreso');
    await userEvent.type(screen.getByLabelText('Contraseña temporal'), 'Temporal123');
    await userEvent.type(screen.getByLabelText('Contraseña nueva'), 'Propia-Sintetica-1');
    await userEvent.type(screen.getByLabelText('Repite la contraseña nueva'), 'Propia-Sintetica-1');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar y continuar' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
    expect(await screen.findByRole('navigation', { name: 'Menú principal' })).toBeInTheDocument();
  });

  it('no deja ir a otra pantalla mientras no la cambie', async () => {
    const { router } = montar('/login?volver=%2Freservas');
    await entrar('temporal@andes.example', 'Temporal123');
    await screen.findByRole('heading', { name: /Crea tu contraseña/ });
    expect(router.state.location.pathname).toBe('/primer-ingreso');
  });

  it('valida antes de enviar y muestra el error del servidor', async () => {
    montar();
    await entrar('temporal@andes.example', 'Temporal123');
    await screen.findByRole('heading', { name: /Crea tu contraseña/ });
    await userEvent.type(screen.getByLabelText('Contraseña nueva'), 'corta');
    await userEvent.type(screen.getByLabelText('Repite la contraseña nueva'), 'otra');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar y continuar' }));
    expect(screen.getByText('Ingresa la contraseña temporal.')).toBeInTheDocument();
    expect(screen.getByText('Mínimo 10 caracteres.')).toBeInTheDocument();
    expect(screen.getByText('Las contraseñas no coinciden.')).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText('Contraseña nueva'));
    await userEvent.clear(screen.getByLabelText('Repite la contraseña nueva'));
    await userEvent.type(screen.getByLabelText('Contraseña temporal'), 'equivocada1');
    await userEvent.type(screen.getByLabelText('Contraseña nueva'), 'Propia-Sintetica-1');
    await userEvent.type(screen.getByLabelText('Repite la contraseña nueva'), 'Propia-Sintetica-1');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar y continuar' }));
    expect(await screen.findByText('La contraseña actual no es correcta.')).toBeInTheDocument();
  });

  it('sin temporal, /primer-ingreso lleva a su vista', async () => {
    const { router } = montar('/login?volver=%2Fprimer-ingreso');
    await entrar('despacho@andes.example', 'clave');
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});
