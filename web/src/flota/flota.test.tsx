/** Administración de flota (HU-10): vehículos, carga CSV, datos del conductor y asociación (CP-01, CP-02). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { MENSAJES } from '../api/errores';
import { hoy } from '../hora/hora';
import { montarPanel } from '../pruebas/montar';
import { conductorDePrueba, informeDePrueba, ServidorFlotaFalso, vehiculoDePrueba } from '../pruebas/servidorFlotaFalso';

const ANIO = Number(hoy().slice(0, 4));
const CRLF = String.fromCharCode(13, 10);
const ADMIN = 'admin@andes.example';

function montar(ruta: string, email = ADMIN) {
  const contexto = montarPanel(ruta, { email });
  const flota = new ServidorFlotaFalso(contexto.servidor);
  return { ...contexto, flota };
}

/** La tabla con datos (no la de espera, que también es una tabla). */
async function tablaConDatos() {
  await screen.findByRole('columnheader', { name: /Patente|Nombre/ });
  return screen.getByRole('table');
}

function cuerpos(flota: ServidorFlotaFalso, ruta: string) {
  return flota.cuerpos.filter((c) => c.ruta === ruta).map((c) => c.cuerpo);
}

describe('menú y permisos', () => {
  it('el administrador ve Vehículos y Conductores en el menú', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getAllByRole('link').map((a) => a.textContent)).toEqual([
      'Inicio',
      'Reservas',
      'Mapa',
      'Vehículos',
      'Conductores',
      'Conversaciones',
      'Reportes',
      'Usuarios',
      'Cierre de caja',
      'Convenios',
    ]);
  });

  it('el despachador no los ve y si entra por URL ve «sin permiso» sin consultar la API', async () => {
    const { servidor } = montar('/vehiculos', 'despacho@andes.example');
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    const menu = screen.getByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).queryByRole('link', { name: 'Vehículos' })).not.toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes('/api/vehiculos/'))).toBe(false);
  });
});

describe('vehículos', () => {
  it('lista con sus conductores y filtra por estado y búsqueda en la URL', async () => {
    const { flota, router } = montar('/vehiculos');
    flota.vehiculos.push(
      vehiculoDePrueba({ patente: 'BCDF10', conductores: [{ id: 1, nombre: 'Pedro Soto' }] }),
      vehiculoDePrueba({ patente: 'GHJK20', marca_modelo: 'Hyundai H-1', activo: false }),
    );
    const tabla = await tablaConDatos();
    expect(within(tabla).getAllByRole('row')).toHaveLength(3);
    expect(within(tabla).getByText('Pedro Soto')).toBeInTheDocument();
    expect(within(tabla).getByText('Inactivo')).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText('Estado'), 'false');
    await waitFor(() => expect(router.state.location.search).toBe('?activo=false'));
    await waitFor(() => expect(within(screen.getByRole('table')).getAllByRole('row')).toHaveLength(2));

    await userEvent.type(screen.getByLabelText('Buscar'), 'zzz');
    await waitFor(() => expect(router.state.location.search).toBe('?activo=false&q=zzz'));
    expect(await screen.findByText('Ningún vehículo coincide con los filtros.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Quitar filtros' }));
    await waitFor(() => expect(router.state.location.search).toBe(''));
    expect(screen.getByLabelText('Buscar')).toHaveValue('');
  });

  it('sin vehículos ofrece registrar o cargar por CSV', async () => {
    montar('/vehiculos');
    expect(await screen.findByText('Aún no hay vehículos registrados.')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Cargar CSV' }).length).toBeGreaterThan(0);
  });

  it('registrar: valida antes de enviar, normaliza la patente y abre la ficha', async () => {
    const { flota, router } = montar('/vehiculos/nuevo');
    await screen.findByRole('heading', { name: 'Nuevo vehículo' });
    await userEvent.type(screen.getByLabelText('Patente'), 'abc12');
    await userEvent.type(screen.getByLabelText('Marca y modelo'), 'Kia   Rio');
    await userEvent.type(screen.getByLabelText('Año'), String(ANIO - 13));
    await userEvent.click(screen.getByRole('button', { name: 'Registrar vehículo' }));
    expect(await screen.findByText('Patente chilena: AB1234 o ABCD12.')).toBeInTheDocument();
    expect(screen.getByText(/antigüedad máxima de 12 años/)).toBeInTheDocument();
    expect(cuerpos(flota, 'POST /api/vehiculos/')).toEqual([]);

    await userEvent.clear(screen.getByLabelText('Patente'));
    await userEvent.type(screen.getByLabelText('Patente'), 'gh-jk 20');
    await userEvent.clear(screen.getByLabelText('Año'));
    await userEvent.type(screen.getByLabelText('Año'), String(ANIO));
    await userEvent.click(screen.getByRole('button', { name: 'Registrar vehículo' }));
    expect(await screen.findByRole('heading', { name: /Vehículo GHJK20/ })).toBeInTheDocument();
    expect(screen.getByText('Vehículo registrado.')).toBeInTheDocument();
    expect(cuerpos(flota, 'POST /api/vehiculos/')).toEqual([
      { patente: 'GHJK20', marca_modelo: 'Kia Rio', anio: ANIO, capacidad: 4 },
    ]);
    expect(router.state.location.pathname).toMatch(/^\/vehiculos\/\d+$/);
  });

  it('registrar: el 400 del backend queda en su campo y lo enfoca', async () => {
    const { flota } = montar('/vehiculos/nuevo');
    flota.vehiculos.push(vehiculoDePrueba({ patente: 'GHJK20' }));
    await screen.findByRole('heading', { name: 'Nuevo vehículo' });
    await userEvent.type(screen.getByLabelText('Patente'), 'GHJK20');
    await userEvent.type(screen.getByLabelText('Marca y modelo'), 'Kia Rio');
    await userEvent.type(screen.getByLabelText('Año'), String(ANIO));
    await userEvent.click(screen.getByRole('button', { name: 'Registrar vehículo' }));
    expect(await screen.findByText('Esta patente ya está registrada.')).toBeInTheDocument();
    expect(screen.getByLabelText('Patente')).toHaveFocus();
    expect(screen.getByLabelText('Patente')).toHaveAttribute('aria-invalid', 'true');
  });

  it('ficha: edita solo lo que cambió y la patente no se toca', async () => {
    const vehiculo = vehiculoDePrueba({ id: 7, patente: 'BCDF10' });
    const { flota } = montar('/vehiculos/7');
    flota.vehiculos.push(vehiculo);
    await screen.findByRole('heading', { name: /Vehículo BCDF10/ });
    expect(screen.getByLabelText('Patente')).toHaveAttribute('readonly');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('No hay cambios que guardar.')).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText('Capacidad (pasajeros)'));
    await userEvent.type(screen.getByLabelText('Capacidad (pasajeros)'), '5');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument();
    expect(cuerpos(flota, 'PATCH /api/vehiculos/7/')).toEqual([{ capacidad: 5 }]);
  });

  it('ficha: desactivar en uso muestra el 409; libre, se desactiva', async () => {
    const vehiculo = vehiculoDePrueba({ id: 7, patente: 'BCDF10' });
    const { flota } = montar('/vehiculos/7');
    flota.vehiculos.push(vehiculo);
    flota.conductores.push(conductorDePrueba({ estado: 'DISPONIBLE', vehiculo_activo: { id: 7, patente: 'BCDF10' } }));
    await userEvent.click(await screen.findByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('declarado por Pedro Soto, que está en turno');

    Object.assign(flota.conductores[0], { estado: 'NO_DISPONIBLE' });
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByText('Vehículo desactivado.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Activar' })).toBeInTheDocument();
  });

  it('ficha inexistente o de otra empresa', async () => {
    montar('/vehiculos/999');
    expect(await screen.findByText('No existe el vehículo o no es de tu empresa.')).toBeInTheDocument();
  });

  it('error de red al cargar: mensaje y reintentar', async () => {
    const { flota } = montar('/vehiculos');
    flota.siguiente('GET /api/vehiculos/', { estado: 503 });
    expect(await screen.findByText(MENSAJES.sin_conexion)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('Aún no hay vehículos registrados.')).toBeInTheDocument();
  });
});

describe('carga por CSV', () => {
  // jsdom reemplaza FormData y File por los suyos, que el Request de Node no sabe serializar (multipart). En el
  // navegador son los mismos; aquí se usan los de Node mientras corren estas pruebas.
  const originales = { FormData: globalThis.FormData, File: globalThis.File };
  beforeAll(async () => {
    // Un multipart mínimo: al leerlo, Node entrega sus propias clases FormData y File.
    const multipart = ['--x', 'Content-Disposition: form-data; name="f"; filename="a.txt"', '', 'hola', '--x--', ''].join(CRLF);
    const formulario = await new Response(multipart, {
      headers: { 'Content-Type': 'multipart/form-data; boundary=x' },
    }).formData();
    Object.assign(globalThis, { FormData: formulario.constructor, File: (formulario.get('f') as object).constructor });
  });
  afterAll(() => {
    Object.assign(globalThis, originales);
  });

  const archivo = () => new File(['patente,marca_modelo,anio\nGHJK20,Kia Rio,2024\n'], 'flota.csv', { type: 'text/csv' });

  it('revisa, muestra el informe y carga', async () => {
    const { flota } = montar('/vehiculos/importar');
    await screen.findByRole('heading', { name: 'Cargar vehículos por CSV' });
    expect(screen.getByRole('button', { name: 'Revisar' })).toBeDisabled();
    await userEvent.upload(screen.getByLabelText('Archivo CSV'), archivo());
    await userEvent.click(screen.getByRole('button', { name: 'Revisar' }));
    const tabla = await screen.findByRole('table', { name: 'Revisión del archivo' });
    expect(within(tabla).getByText('GHJK20')).toBeInTheDocument();
    expect(within(tabla).getByText('Lista')).toBeInTheDocument();

    flota.informes.push({ estado: 201, cuerpo: informeDePrueba({ creados: 1 }) });
    await userEvent.click(screen.getByRole('button', { name: 'Cargar 1 vehículo' }));
    expect(await screen.findByText('Se cargó 1 vehículo.')).toBeInTheDocument();
    expect(cuerpos(flota, 'POST /api/vehiculos/importar/')).toEqual([
      { archivo: 'flota.csv', confirmar: 'false' },
      { archivo: 'flota.csv', confirmar: 'true' },
    ]);
  });

  it('con errores por línea no ofrece cargar', async () => {
    const { flota } = montar('/vehiculos/importar');
    flota.informes.push({
      estado: 200,
      cuerpo: informeDePrueba({
        filas: [{ linea: 3, datos: { patente: 'ABC123', marca_modelo: 'Kia Rio', anio: '2024' }, errores: { patente: ['Patente chilena: AB1234 o ABCD12.'] } }],
        validas: 0,
        con_errores: 1,
      }),
    });
    await userEvent.upload(await screen.findByLabelText('Archivo CSV'), archivo());
    await userEvent.click(screen.getByRole('button', { name: 'Revisar' }));
    expect(await screen.findByText('Patente: Patente chilena: AB1234 o ABCD12.')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Cargar/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Corrige las líneas con errores/)).toBeInTheDocument();
  });

  it('al confirmar, un 400 con informe avisa que no se cargó nada', async () => {
    const { flota } = montar('/vehiculos/importar');
    await userEvent.upload(await screen.findByLabelText('Archivo CSV'), archivo());
    await userEvent.click(screen.getByRole('button', { name: 'Revisar' }));
    flota.informes.push({
      estado: 400,
      cuerpo: informeDePrueba({
        filas: [{ linea: 2, datos: { patente: 'GHJK20' }, errores: { patente: ['Esta patente ya está registrada.'] } }],
        validas: 0,
        con_errores: 1,
      }),
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Cargar 1 vehículo' }));
    expect(await screen.findByText('No se cargó ningún vehículo: hay líneas con errores.')).toBeInTheDocument();
    expect(screen.getByText('Patente: Esta patente ya está registrada.')).toBeInTheDocument();
  });

  it('un archivo que no sirve muestra el motivo', async () => {
    const { flota } = montar('/vehiculos/importar');
    flota.informes.push({ estado: 400, cuerpo: { archivo: ['Faltan columnas: anio.'] } });
    await userEvent.upload(await screen.findByLabelText('Archivo CSV'), archivo());
    await userEvent.click(screen.getByRole('button', { name: 'Revisar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Faltan columnas: anio.');
  });
});

describe('conductores', () => {
  it('lista con licencia por vencer y cuenta deshabilitada', async () => {
    const { flota } = montar('/conductores');
    const pronto = hoy(Date.now() + 10 * 86_400_000);
    flota.conductores.push(
      conductorDePrueba({ nombre: 'Pedro Soto', licencia_vence: pronto, vehiculos: [{ id: 1, patente: 'BCDF10', marca_modelo: 'Toyota Yaris', activo: true, desde: '2026-01-01' }] }),
      conductorDePrueba({ nombre: 'Ana Ríos', activo: false, estado: 'DISPONIBLE' }),
    );
    const tabla = await tablaConDatos();
    expect(within(tabla).getByText('Vence en 10 días')).toBeInTheDocument();
    expect(within(tabla).getByText('BCDF10')).toBeInTheDocument();
    expect(within(tabla).getByText('Cuenta deshabilitada')).toBeInTheDocument();
    expect(within(tabla).getByText('Disponible')).toBeInTheDocument();
  });

  it('editar datos: valida, normaliza y envía solo lo que cambió', async () => {
    const { flota } = montar('/conductores/40');
    flota.conductores.push(conductorDePrueba({ id: 40 }));
    await userEvent.click(await screen.findByRole('button', { name: 'Editar datos' }));
    await userEvent.clear(screen.getByLabelText('RUT'));
    await userEvent.type(screen.getByLabelText('RUT'), '12.345.678-9');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar datos' }));
    expect(await screen.findByText('RUT inválido: revisa el dígito verificador.')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('RUT'));
    await userEvent.type(screen.getByLabelText('RUT'), '12.345.678-5');
    await userEvent.clear(screen.getByLabelText('Teléfono'));
    await userEvent.type(screen.getByLabelText('Teléfono'), '9 0000 1234');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar datos' }));
    expect(await screen.findByText('Datos guardados.')).toBeInTheDocument();
    expect(cuerpos(flota, 'PATCH /api/conductores/40/')).toEqual([{ rut: '12345678-5', telefono: '+56900001234' }]);
    expect(screen.getByText('12345678-5')).toBeInTheDocument();
  });

  it('editar datos: el 400 del backend va a su campo', async () => {
    const { flota } = montar('/conductores/40');
    flota.conductores.push(conductorDePrueba({ id: 40 }));
    flota.siguiente('PATCH /api/conductores/40/', { estado: 400, cuerpo: { rut: ['Este RUT ya está registrado.'] } });
    await userEvent.click(await screen.findByRole('button', { name: 'Editar datos' }));
    await userEvent.clear(screen.getByLabelText('RUT'));
    await userEvent.type(screen.getByLabelText('RUT'), '12345678-5');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar datos' }));
    expect(await screen.findByText('Este RUT ya está registrado.')).toBeInTheDocument();
    expect(screen.getByLabelText('RUT')).toHaveFocus();
  });

  it('asocia un vehículo activo y no quita el declarado en turno', async () => {
    const { flota } = montar('/conductores/40');
    flota.vehiculos.push(
      vehiculoDePrueba({ id: 1, patente: 'BCDF10' }),
      vehiculoDePrueba({ id: 2, patente: 'GHJK20' }),
    );
    flota.conductores.push(
      conductorDePrueba({
        id: 40,
        estado: 'DISPONIBLE',
        vehiculo_activo: { id: 1, patente: 'BCDF10' },
        vehiculos: [{ id: 1, patente: 'BCDF10', marca_modelo: 'Toyota Yaris', activo: true, desde: '2026-01-01' }],
      }),
    );
    const paraAsociar = await screen.findByRole('list', { name: 'Vehículos para asociar' });
    // El ya asociado no se ofrece.
    expect(within(paraAsociar).getAllByRole('listitem')).toHaveLength(1);
    await userEvent.click(within(paraAsociar).getByRole('button', { name: 'Asociar GHJK20' }));
    const asociados = await screen.findByRole('list', { name: 'Vehículos asociados' });
    await waitFor(() => expect(within(asociados).getAllByRole('listitem')).toHaveLength(2));
    expect(cuerpos(flota, 'POST /api/conductores/40/vehiculos/')).toEqual([{ vehiculo: 2 }]);
    expect(within(asociados).getByText(/declarado para el turno/)).toBeInTheDocument();

    await userEvent.click(within(asociados).getByRole('button', { name: 'Quitar BCDF10' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Es el vehículo declarado del turno en curso.');
    await userEvent.click(within(asociados).getByRole('button', { name: 'Quitar GHJK20' }));
    await waitFor(() => expect(within(screen.getByRole('list', { name: 'Vehículos asociados' })).getAllByRole('listitem')).toHaveLength(1));
  });

  it('asociar: el 400 del backend se muestra', async () => {
    const { flota } = montar('/conductores/40');
    flota.vehiculos.push(vehiculoDePrueba({ id: 2, patente: 'GHJK20' }));
    flota.conductores.push(conductorDePrueba({ id: 40 }));
    flota.siguiente('POST /api/conductores/40/vehiculos/', { estado: 400, cuerpo: { vehiculo: ['El vehículo está inactivo.'] } });
    await userEvent.click(await screen.findByRole('button', { name: 'Asociar GHJK20' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El vehículo está inactivo.');
  });

  it('conductor inexistente', async () => {
    montar('/conductores/abc');
    expect(await screen.findByText('No existe el conductor o no es de tu empresa.')).toBeInTheDocument();
  });
});
