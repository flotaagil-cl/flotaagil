/** HU-45: «Mi perfil» del pasajero (DC-50). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { mesYAnio, telefonoLegible } from './perfil';

const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

const PERFIL = {
  nombre: 'Pablo Pasajero',
  email: 'pasajero@andes.example',
  telefono: '+56987654321',
  empresa: 'Transportes Andes Demo SpA',
  empresa_slug: 'transportes-andes',
  telefono_pendiente: null as string | null,
  pasajero_desde: '2026-10-05T14:00:00Z',
  password_cambiada_en: null as string | null,
};

interface Opciones {
  patch?: (cuerpo: Record<string, string>) => Response;
  eliminar?: () => Response;
}

function montar({ patch, eliminar }: Opciones = {}) {
  const servidor = new ServidorAuthFalso();
  const llamadas: { ruta: string; cuerpo?: unknown }[] = [];
  let perfil = { ...PERFIL };
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const ruta = `${peticion.method} ${new URL(peticion.url).pathname}`;
    if (ruta === 'GET /api/mi-cuenta/') {
      llamadas.push({ ruta });
      return json(200, perfil);
    }
    if (ruta === 'PATCH /api/mi-cuenta/') {
      const cuerpo = (await peticion.json()) as Record<string, string>;
      llamadas.push({ ruta, cuerpo });
      if (patch) return patch(cuerpo);
      perfil = { ...perfil, nombre: cuerpo.nombre, telefono_pendiente: cuerpo.telefono !== perfil.telefono ? cuerpo.telefono : null };
      return json(200, perfil);
    }
    if (ruta === 'DELETE /api/mi-cuenta/') {
      llamadas.push({ ruta });
      return eliminar ? eliminar() : new Response(null, { status: 204 });
    }
    return original(peticion);
  };
  return { ...montarPanel('/mi-perfil', { email: 'pasajero@andes.example', servidor }), llamadas };
}

describe('HU-45 · funciones', () => {
  it('mes y año, y teléfono legible', () => {
    expect([mesYAnio('2026-10-05T14:00:00Z'), mesYAnio(null)]).toEqual(['oct 2026', null]);
    expect([telefonoLegible('+56987654321'), telefonoLegible('+5412345678')]).toEqual(['+56 9 8765 4321', '+5412345678']);
  });
});

describe('HU-45 · Mi perfil', () => {
  it('muestra los datos y el correo solo de lectura', async () => {
    montar();
    expect(await screen.findByRole('heading', { level: 1, name: 'Mi perfil' })).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre y apellido')).toHaveValue('Pablo Pasajero');
    const correo = screen.getByLabelText('Correo');
    expect(correo).toHaveValue('pasajero@andes.example');
    expect(correo).toHaveAttribute('readonly');
    expect(screen.getByText('Para cambiar tu correo, contacta a la empresa.')).toBeInTheDocument();
    expect(screen.getByText('Pasajero desde oct 2026')).toBeInTheDocument();
    expect(screen.getByText('Nunca la has cambiado')).toBeInTheDocument();
  });

  it('guarda el nombre y avisa que el WhatsApp nuevo se confirma', async () => {
    const { llamadas } = montar();
    const nombre = await screen.findByLabelText('Nombre y apellido');
    await userEvent.clear(nombre);
    await userEvent.type(nombre, 'Pablo Andrés Pasajero');
    const whatsapp = screen.getByLabelText('WhatsApp');
    await userEvent.clear(whatsapp);
    await userEvent.type(whatsapp, '+56911112222');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await waitFor(() => expect(llamadas.find((l) => l.ruta === 'PATCH /api/mi-cuenta/')?.cuerpo).toEqual({ nombre: 'Pablo Andrés Pasajero', telefono: '+56911112222' }));
    expect(await screen.findByText(/Te enviamos un WhatsApp al \+56 9 1111 2222/)).toHaveTextContent('te seguimos escribiendo al +56 9 8765 4321');
    // El nombre nuevo también se ve en la cabecera.
    expect(await screen.findByRole('button', { name: /Pablo Andrés Pasajero.*menú de la cuenta/ })).toBeInTheDocument();
  });

  it('no envía sin nombre y muestra el WhatsApp de otra cuenta', async () => {
    const { llamadas } = montar({ patch: () => json(409, { detail: 'Ese WhatsApp ya está asociado a otra cuenta de esta empresa.', code: 'telefono_en_uso' }) });
    const nombre = await screen.findByLabelText('Nombre y apellido');
    await userEvent.clear(nombre);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Escribe tu nombre y apellido.')).toBeInTheDocument();
    expect(llamadas.some((l) => l.ruta === 'PATCH /api/mi-cuenta/')).toBe(false);
    await userEvent.type(nombre, 'Pablo Pasajero');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Ese WhatsApp ya está asociado a otra cuenta de esta empresa.')).toBeInTheDocument();
  });

  it('cambia la contraseña y sigue con la sesión', async () => {
    const { router } = montar();
    await userEvent.click(await screen.findByRole('button', { name: /Cambiar contraseña/ }));
    const dialogo = screen.getByRole('dialog', { name: 'Cambiar contraseña' });
    await userEvent.type(within(dialogo).getByLabelText('Contraseña actual'), 'clave');
    await userEvent.type(within(dialogo).getByLabelText('Contraseña nueva'), 'Nueva-Clave-2026');
    await userEvent.type(within(dialogo).getByLabelText('Repite la contraseña nueva'), 'Nueva-Clave-2026');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cambiar contraseña' }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Cambiar contraseña' })).not.toBeInTheDocument());
    expect(router.state.location.pathname).toBe('/mi-perfil');
  });

  it('eliminar pide escribir ELIMINAR, explica qué se conserva y cierra la sesión', async () => {
    const { router, llamadas } = montar();
    await userEvent.click(await screen.findByRole('button', { name: /Eliminar mi cuenta/ }));
    const dialogo = screen.getByRole('dialog', { name: '¿Eliminar tu cuenta?' });
    expect(within(dialogo).getByText(/Tus viajes, sus pagos y su historial/)).toBeInTheDocument();
    const boton = within(dialogo).getByRole('button', { name: 'Eliminar mi cuenta' });
    expect(boton).toBeDisabled();
    await userEvent.type(within(dialogo).getByLabelText('Escribe ELIMINAR para confirmar'), 'eliminar');
    expect(boton).toBeEnabled();
    await userEvent.click(boton);
    await waitFor(() => expect(router.state.location.pathname).toBe('/solicitar/transportes-andes/ingresar'));
    expect(llamadas.map((l) => l.ruta)).toContain('DELETE /api/mi-cuenta/');
  });

  it('con un viaje en curso no elimina y lo explica', async () => {
    const { router } = montar({ eliminar: () => json(409, { detail: 'Tienes un viaje en curso.', code: 'viaje_activo' }) });
    await userEvent.click(await screen.findByRole('button', { name: /Eliminar mi cuenta/ }));
    const dialogo = screen.getByRole('dialog', { name: '¿Eliminar tu cuenta?' });
    await userEvent.type(within(dialogo).getByLabelText('Escribe ELIMINAR para confirmar'), 'ELIMINAR');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Eliminar mi cuenta' }));
    expect(await within(dialogo).findByRole('alert')).toHaveTextContent('Podrás eliminar tu cuenta cuando termine o lo canceles.');
    expect(router.state.location.pathname).toBe('/mi-perfil');
  });

  it('cerrar sesión vuelve al ingreso del portal', async () => {
    const { router } = montar();
    await userEvent.click(await screen.findByRole('button', { name: /Cerrar sesión/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/solicitar/transportes-andes/ingresar'));
  });

  it('la ruta antigua «Mis reservas» lleva a «Mis viajes» (HU-44)', async () => {
    const { router } = montarPanel('/mis-reservas', { email: 'pasajero@andes.example' });
    await waitFor(() => expect(router.state.location.pathname).toBe('/mis-viajes'));
  });

  it('otro rol no ve Mi perfil', async () => {
    const { router } = montarPanel('/mi-perfil');
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});
