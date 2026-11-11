/** HU-36: usuarios del panel. */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';

const ADMIN = { id: 1, nombre: 'Ana Admin', email: 'admin@andes.example', rol: 'ADMINISTRADOR', activo: true, acceso: 'ACTIVA', last_login: null };
const DESPACHO = { id: 2, nombre: 'Diego Despacho', email: 'despacho@andes.example', rol: 'DESPACHADOR', activo: true, acceso: 'ACTIVA', last_login: null };

function instalar(auth: ServidorAuthFalso, programada?: Respuesta) {
  const anterior = auth.api;
  let usuarios = [{ ...ADMIN }, { ...DESPACHO }];
  const llamadas: { ruta: string; cuerpo?: unknown }[] = [];
  auth.api = async (peticion: Request, url: URL): Promise<Respuesta> => {
    if (!url.pathname.startsWith('/api/usuarios/')) return anterior!(peticion, url);
    const ruta = `${peticion.method} ${url.pathname}`;
    const texto = peticion.method === 'GET' ? '' : await peticion.text();
    const cuerpo = texto ? JSON.parse(texto) : undefined;
    llamadas.push({ ruta, cuerpo });
    if (ruta === 'GET /api/usuarios/') return { estado: 200, cuerpo: { count: usuarios.length, next: null, previous: null, results: usuarios } };
    if (programada) return programada;
    if (ruta === 'POST /api/usuarios/') {
      const nuevo = { id: 3, ...cuerpo, activo: true, acceso: 'TEMPORAL', last_login: null };
      usuarios = [...usuarios, nuevo];
      return { estado: 201, cuerpo: { ...nuevo, password_temporal: 'TmpSintetica23', vence_en: '2026-07-18T12:00:00Z' } };
    }
    const m = /^\/api\/usuarios\/(\d+)\/(?:(desactivar|activar|password)\/)?$/.exec(url.pathname);
    const id = Number(m?.[1]);
    if (m?.[2] === 'password') return { estado: 201, cuerpo: { password_temporal: 'OtraTmp45', vence_en: '2026-07-18T12:00:00Z' } };
    usuarios = usuarios.map((u) =>
      u.id !== id ? u : m?.[2] === 'desactivar' ? { ...u, activo: false } : m?.[2] === 'activar' ? { ...u, activo: true } : { ...u, ...cuerpo },
    );
    return { estado: 200, cuerpo: usuarios.find((u) => u.id === id) };
  };
  return llamadas;
}

const montar = (email = 'admin@andes.example') => {
  const contexto = montarPanel('/usuarios', { email });
  return contexto;
};

describe('usuarios del panel', () => {
  it('el administrador lo ve en el menú; el despachador no y por URL ve «sin permiso»', async () => {
    const { servidor } = montarPanel('/', { email: 'admin@andes.example' });
    instalar(servidor);
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Usuarios' })).toBeInTheDocument();
  });

  it('el despachador por URL ve «sin permiso»', async () => {
    const { servidor } = montar('despacho@andes.example');
    const llamadas = instalar(servidor);
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    expect(llamadas).toEqual([]);
  });

  it('lista y marca la propia cuenta, sin ofrecer desactivarse', async () => {
    const { servidor } = montar();
    instalar(servidor);
    const tabla = await screen.findByRole('table', { name: 'Usuarios del panel' });
    const propia = within(tabla).getByText(/Ana Admin \(tú\)/).closest('tr')!;
    expect(within(propia).queryByRole('button', { name: 'Desactivar' })).not.toBeInTheDocument();
    const otra = within(tabla).getByText('Diego Despacho').closest('tr')!;
    expect(within(otra).getByRole('button', { name: 'Desactivar' })).toBeInTheDocument();
  });

  it('crea y muestra la temporal una sola vez', async () => {
    const { servidor } = montar();
    const llamadas = instalar(servidor);
    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo usuario' }));
    const formulario = screen.getByRole('form', { name: 'Nuevo usuario' });
    await userEvent.type(within(formulario).getByLabelText('Nombre'), 'Sara Sintética');
    await userEvent.type(within(formulario).getByLabelText('Correo'), 'sara@andes.example');
    await userEvent.selectOptions(within(formulario).getByLabelText('Rol'), 'Administrador');
    await userEvent.click(within(formulario).getByRole('button', { name: 'Crear usuario' }));
    const dialogo = await screen.findByRole('dialog');
    expect(within(dialogo).getByText('TmpSintetica23')).toBeInTheDocument();
    expect(llamadas.find((l) => l.ruta === 'POST /api/usuarios/')?.cuerpo).toEqual({ nombre: 'Sara Sintética', email: 'sara@andes.example', rol: 'ADMINISTRADOR' });
  });

  it('el correo usado queda en su campo', async () => {
    const { servidor } = montar();
    instalar(servidor, { estado: 400, cuerpo: { email: ['Ese correo ya tiene una cuenta en FlotaÁgil.'] } });
    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo usuario' }));
    await userEvent.type(screen.getByLabelText('Nombre'), 'X');
    await userEvent.type(screen.getByLabelText('Correo'), 'usado@andes.example');
    await userEvent.click(screen.getByRole('button', { name: 'Crear usuario' }));
    expect(await screen.findByText('Ese correo ya tiene una cuenta en FlotaÁgil.')).toBeInTheDocument();
  });

  it('no puede cambiar su propio rol', async () => {
    const { servidor } = montar();
    instalar(servidor);
    const propia = (await screen.findByText(/Ana Admin \(tú\)/)).closest('tr')!;
    await userEvent.click(within(propia).getByRole('button', { name: 'Editar' }));
    expect(screen.getByLabelText('Rol')).toBeDisabled();
    expect(screen.getByText('No puedes cambiar tu propio rol.')).toBeInTheDocument();
  });

  it('desactivar pide confirmación y se puede activar de nuevo', async () => {
    const { servidor } = montar();
    const llamadas = instalar(servidor);
    const fila = (await screen.findByText('Diego Despacho')).closest('tr')!;
    await userEvent.click(within(fila).getByRole('button', { name: 'Desactivar' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByText(/sus sesiones se cerraron/)).toBeInTheDocument();
    await waitFor(() => expect(within(screen.getByText('Diego Despacho').closest('tr')!).getByText('Desactivado')).toBeInTheDocument());
    await userEvent.click(within(screen.getByText('Diego Despacho').closest('tr')!).getByRole('button', { name: 'Activar' }));
    await waitFor(() => expect(llamadas.some((l) => l.ruta === 'POST /api/usuarios/2/activar/')).toBe(true));
  });

  it('el 409 del último administrador se muestra', async () => {
    const { servidor } = montar();
    instalar(servidor, { estado: 409, cuerpo: { detail: 'La empresa debe tener al menos un administrador activo.', code: 'ultimo_administrador' } });
    const fila = (await screen.findByText('Diego Despacho')).closest('tr')!;
    await userEvent.click(within(fila).getByRole('button', { name: 'Desactivar' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByText('La empresa debe tener al menos un administrador activo.')).toBeInTheDocument();
  });

  it('restablecer muestra la nueva temporal', async () => {
    const { servidor } = montar();
    instalar(servidor);
    const fila = (await screen.findByText('Diego Despacho')).closest('tr')!;
    await userEvent.click(within(fila).getByRole('button', { name: 'Restablecer contraseña' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Restablecer' }));
    expect(within(await screen.findByRole('dialog')).getByText('OtraTmp45')).toBeInTheDocument();
  });
});
