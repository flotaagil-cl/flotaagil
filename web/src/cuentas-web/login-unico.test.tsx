/** HU-33: un solo inicio de sesión web; cada rol llega a su vista. */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { App } from '../App';
import { createMemoryRouter } from 'react-router';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { crearRutas, inicioDeRol } from '../rutas/tabla';

function montarLogin(ruta = '/login') {
  const servidor = new ServidorAuthFalso();
  const { entorno } = crearEntorno({ servidor, locks: crearLocks() });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { servidor, router };
}

async function entrar(email: string) {
  await userEvent.type(await screen.findByLabelText('Correo'), email);
  await userEvent.type(screen.getByLabelText('Contraseña'), 'clave');
  await userEvent.click(screen.getByRole('button', { name: /Ingresar|Entrar/ }));
}

describe('destino por rol', () => {
  it.each([
    ['ADMINISTRADOR', '/'],
    ['DESPACHADOR', '/'],
    ['CONVENIO', '/mi-convenio'],
    ['PASAJERO', '/mis-reservas'],
  ] as const)('%s → %s', (rol, ruta) => {
    expect(inicioDeRol(rol)).toBe(ruta);
  });

  it('el convenio entra por el mismo login y llega a «Mi convenio»', async () => {
    const { router } = montarLogin();
    await entrar('convenio@andes.example');
    expect(await screen.findByRole('heading', { name: 'Mi convenio' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/mi-convenio');
  });

  it('el pasajero llega a «Mis reservas»', async () => {
    const { router } = montarLogin();
    await entrar('pasajero@andes.example');
    expect(await screen.findByRole('heading', { name: 'Mis reservas' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/mis-reservas');
  });

  it('el login ofrece recuperar la contraseña', async () => {
    montarLogin();
    expect(await screen.findByRole('link', { name: '¿Olvidaste tu contraseña?' })).toHaveAttribute('href', '/recuperar');
  });

  it('el despachador sigue llegando a Inicio', async () => {
    const { router } = montarLogin();
    await entrar('despacho@andes.example');
    await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(router.state.location.pathname).toBe('/');
  });

  it('con «volver» se respeta el destino', async () => {
    const { router } = montarLogin('/login?volver=%2Fsolicitar%2Ftransportes-andes');
    await entrar('pasajero@andes.example');
    await waitFor(() => expect(router.state.location.pathname).toBe('/solicitar/transportes-andes'));
  });

  it('el conductor sigue rechazado', async () => {
    montarLogin();
    await entrar('conductor@andes.example');
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});

describe('marco por rol', () => {
  it('el pasajero solo ve su menú, sin alertas de vuelo ni pantallas del panel', async () => {
    const { servidor } = montarPanel('/mis-reservas', { email: 'pasajero@andes.example' });
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getAllByRole('link').map((l) => l.textContent)).toEqual(['Mis reservas']);
    expect(screen.getByText(/Pablo Pasajero · Pasajero/)).toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes('/api/alertas/'))).toBe(false);
  });

  it('en «/» el convenio va a su vista', async () => {
    const { router } = montarPanel('/', { email: 'convenio@andes.example' });
    expect(await screen.findByRole('heading', { name: 'Mi convenio' })).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/mi-convenio');
  });

  it('por URL el convenio no entra al panel', async () => {
    montarPanel('/reservas', { email: 'convenio@andes.example' });
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
  });
});
