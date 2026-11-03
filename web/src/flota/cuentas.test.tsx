/** Cuentas de los conductores (HU-10, PR-06): alta, contraseña temporal, habilitación y carga por CSV. */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';
import { hoy } from '../hora/hora';
import { montarPanel } from '../pruebas/montar';
import { conductorDePrueba, informeDePrueba, ServidorFlotaFalso } from '../pruebas/servidorFlotaFalso';

const ANIO = Number(hoy().slice(0, 4));
const CRLF = String.fromCharCode(13, 10);

function montar(ruta: string) {
  const contexto = montarPanel(ruta, { email: 'admin@andes.example' });
  return { ...contexto, flota: new ServidorFlotaFalso(contexto.servidor) };
}

function cuerpos(flota: ServidorFlotaFalso, ruta: string) {
  return flota.cuerpos.filter((c) => c.ruta === ruta).map((c) => c.cuerpo);
}

async function llenarAlta(correo = 'Rosa@Flota.example') {
  await screen.findByRole('heading', { name: 'Nuevo conductor' });
  await userEvent.type(screen.getByLabelText('Nombre'), 'Rosa Pérez');
  await userEvent.type(screen.getByLabelText('Correo de acceso'), correo);
  await userEvent.type(screen.getByLabelText('RUT'), '12.345.678-5');
  await userEvent.type(screen.getByLabelText('Teléfono'), '9 0000 1234');
  await userEvent.type(screen.getByLabelText('Vencimiento de la licencia'), `${ANIO + 2}-06-30`);
  await userEvent.click(screen.getByRole('button', { name: 'Registrar conductor' }));
}

describe('alta', () => {
  it('valida, normaliza y abre la ficha pidiendo generar la contraseña', async () => {
    const { flota } = montar('/conductores/nuevo');
    await llenarAlta();
    expect(await screen.findByText(/Conductor registrado. Genera su contraseña temporal/)).toBeInTheDocument();
    expect(cuerpos(flota, 'POST /api/conductores/')).toEqual([
      {
        nombre: 'Rosa Pérez',
        email: 'rosa@flota.example',
        rut: '12345678-5',
        telefono: '+56900001234',
        licencia_clase: 'A2',
        licencia_vence: `${ANIO + 2}-06-30`,
      },
    ]);
    expect(screen.getByText('Sin contraseña: todavía no puede ingresar a la app.')).toBeInTheDocument();
  });

  it('el correo repetido queda en su campo', async () => {
    const { flota } = montar('/conductores/nuevo');
    flota.siguiente('POST /api/conductores/', { estado: 400, cuerpo: { email: ['Este correo ya tiene una cuenta.'] } });
    await llenarAlta();
    expect(await screen.findByText('Este correo ya tiene una cuenta.')).toBeInTheDocument();
    expect(screen.getByLabelText('Correo de acceso')).toHaveFocus();
  });

  it('correo inválido no se envía', async () => {
    const { flota } = montar('/conductores/nuevo');
    await llenarAlta('rosa@');
    expect(await screen.findByText('Correo inválido.')).toBeInTheDocument();
    expect(cuerpos(flota, 'POST /api/conductores/')).toEqual([]);
  });
});

describe('contraseña temporal y habilitación', () => {
  it('confirma, la muestra una vez con copiar y al cerrar desaparece', async () => {
    const { flota } = montar('/conductores/40');
    flota.conductores.push(conductorDePrueba({ id: 40, acceso: 'SIN_PASSWORD' }));
    const portapapeles = { writeText: vi.fn().mockResolvedValue(undefined) };
    Object.defineProperty(navigator, 'clipboard', { value: portapapeles, configurable: true });

    await userEvent.click(await screen.findByRole('button', { name: 'Generar contraseña temporal' }));
    expect(screen.getByText(/Se mostrará una sola vez/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Generar' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Contraseña temporal' });
    const temporal = flota.ultimaTemporal!;
    expect(within(dialogo).getByLabelText('Contraseña temporal')).toHaveTextContent(temporal);
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Copiar' }));
    expect(portapapeles.writeText).toHaveBeenCalledWith(temporal);
    expect(await within(dialogo).findByText('Copiada.')).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Listo' }));
    await waitFor(() => expect(screen.queryByText(temporal)).not.toBeInTheDocument());
    expect(await screen.findByText(/Con contraseña temporal: debe cambiarla/)).toBeInTheDocument();
    // Nada quedó en el almacenamiento del navegador.
    expect(JSON.stringify({ ...localStorage, ...sessionStorage })).not.toContain(temporal);
    expect(screen.getByRole('button', { name: 'Restablecer contraseña' })).toBeInTheDocument();
  });

  it('si no se puede copiar, avisa', async () => {
    const { flota } = montar('/conductores/40');
    flota.conductores.push(conductorDePrueba({ id: 40 }));
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockRejectedValue(new Error('no')) },
      configurable: true,
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Restablecer contraseña' }));
    await userEvent.click(screen.getByRole('button', { name: 'Generar' }));
    await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Copiar' }));
    expect(await screen.findByText(/No se pudo copiar/)).toBeInTheDocument();
  });

  it('restablecer en viaje muestra el 409 y no abre el diálogo', async () => {
    const { flota } = montar('/conductores/40');
    flota.conductores.push(conductorDePrueba({ id: 40, estado: 'EN_VIAJE' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Restablecer contraseña' }));
    expect(screen.getByText(/se cerrarán todas las sesiones del conductor/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Generar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El conductor está en viaje');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('deshabilitar con confirmación y volver a habilitar', async () => {
    const { flota } = montar('/conductores/40');
    flota.conductores.push(conductorDePrueba({ id: 40, estado: 'DISPONIBLE', vehiculo_activo: { id: 1, patente: 'BCDF10' } }));
    await userEvent.click(await screen.findByRole('button', { name: 'Deshabilitar cuenta' }));
    await userEvent.click(screen.getByRole('button', { name: 'Volver' }));
    await userEvent.click(screen.getByRole('button', { name: 'Deshabilitar cuenta' }));
    await userEvent.click(within(screen.getByRole('group', { name: 'Confirmar' })).getByRole('button', { name: 'Deshabilitar' }));
    expect(await screen.findByText('Cuenta deshabilitada. Sus sesiones se cerraron.')).toBeInTheDocument();
    expect(screen.getByText('Deshabilitada: no puede ingresar a la app.')).toBeInTheDocument();
    expect(screen.getByText(/No disponible/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Habilitar cuenta' }));
    expect(await screen.findByText('Cuenta habilitada.')).toBeInTheDocument();
  });

  it('el listado marca las cuentas sin acceso y ofrece alta y CSV', async () => {
    const { flota } = montar('/conductores');
    flota.conductores.push(conductorDePrueba({ nombre: 'Rosa', acceso: 'SIN_PASSWORD' }), conductorDePrueba({ nombre: 'Leo', acceso: 'TEMPORAL_VENCIDA' }));
    await screen.findByRole('columnheader', { name: 'Nombre' });
    const tabla = screen.getByRole('table');
    expect(within(tabla).getByText('Sin contraseña')).toBeInTheDocument();
    expect(within(tabla).getByText('Temporal vencida')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Nuevo conductor' })).toHaveAttribute('href', '/conductores/nuevo');
    expect(screen.getByRole('link', { name: 'Cargar CSV' })).toHaveAttribute('href', '/conductores/importar');
  });
});

describe('carga de conductores por CSV', () => {
  // Igual que en flota.test.tsx: FormData y File de Node para que el Request sepa armar el multipart.
  const originales = { FormData: globalThis.FormData, File: globalThis.File };
  beforeAll(async () => {
    const multipart = ['--x', 'Content-Disposition: form-data; name="f"; filename="a.txt"', '', 'hola', '--x--', ''].join(CRLF);
    const formulario = await new Response(multipart, {
      headers: { 'Content-Type': 'multipart/form-data; boundary=x' },
    }).formData();
    Object.assign(globalThis, { FormData: formulario.constructor, File: (formulario.get('f') as object).constructor });
  });
  afterAll(() => {
    Object.assign(globalThis, originales);
  });

  it('revisa y carga, sin contraseñas', async () => {
    const { flota } = montar('/conductores/importar');
    expect(await screen.findByText(/El archivo no lleva contraseñas/)).toBeInTheDocument();
    flota.informes.push({
      estado: 200,
      cuerpo: informeDePrueba({
        filas: [
          {
            linea: 2,
            datos: { nombre: 'Rosa', email: 'rosa@x.example', rut: '12345678-5', telefono: '912345678', licencia_clase: 'A2', licencia_vence: '31-12-2027' },
            errores: {},
          },
        ],
      }),
    });
    const archivo = new File(['nombre;email\n'], 'conductores.csv', { type: 'text/csv' });
    await userEvent.upload(screen.getByLabelText('Archivo CSV'), archivo);
    await userEvent.click(screen.getByRole('button', { name: 'Revisar' }));
    expect(await screen.findByText('rosa@x.example')).toBeInTheDocument();
    flota.informes.push({ estado: 201, cuerpo: informeDePrueba({ creados: 1 }) });
    await userEvent.click(screen.getByRole('button', { name: 'Cargar 1 conductor' }));
    expect(await screen.findByText('Se cargó 1 conductor.')).toBeInTheDocument();
    expect(cuerpos(flota, 'POST /api/conductores/importar/')).toEqual([
      { archivo: 'conductores.csv', confirmar: 'false' },
      { archivo: 'conductores.csv', confirmar: 'true' },
    ]);
  });
});
