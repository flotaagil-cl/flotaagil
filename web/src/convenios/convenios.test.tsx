/** HU-11 y HU-34: administrar convenios con autoregistro y aprobación (RN-08, RN-12). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { convenioDePrueba, ServidorConveniosFalso } from '../pruebas/servidorConveniosFalso';

const ADMIN = 'admin@andes.example';

function montar(ruta: string, email = ADMIN) {
  const contexto = montarPanel(ruta, { email });
  const convenios = new ServidorConveniosFalso(contexto.servidor);
  return { ...contexto, convenios };
}

describe('permisos', () => {
  it('el administrador ve Convenios en el menú', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Convenios' })).toBeInTheDocument();
  });

  it('el despachador no lo ve y por URL ve «sin permiso» sin consultar la API', async () => {
    const { servidor } = montar('/convenios', 'despacho@andes.example');
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes('/api/convenios/'))).toBe(false);
  });
});

describe('listado', () => {
  it('muestra el volumen de reservas y el estado', async () => {
    const { convenios } = montar('/convenios');
    convenios.convenios = [
      convenioDePrueba({ id: 1, cliente_nombre: 'Minera Norte', reservas: 1234 }),
      convenioDePrueba({ id: 2, cliente_nombre: 'Banco Sur', estado: 'EN_REVISION', activo: false, reservas: 0 }),
    ];
    const enlace = await screen.findByRole('link', { name: 'Minera Norte' });
    const fila = enlace.closest('tr')!;
    expect(within(fila).getByText('1.234')).toBeInTheDocument();
    expect(within(fila).getByText('Aprobado')).toBeInTheDocument();
    expect(within(screen.getByRole('link', { name: 'Banco Sur' }).closest('tr')!).getByText('En revisión')).toBeInTheDocument();
  });

  it('filtra por estado', async () => {
    const { convenios } = montar('/convenios');
    convenios.convenios = [
      convenioDePrueba({ cliente_nombre: 'Minera Norte' }),
      convenioDePrueba({ cliente_nombre: 'Banco Sur', estado: 'EN_REVISION', activo: false }),
    ];
    await screen.findByRole('link', { name: 'Minera Norte' });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Estado' }), 'En revisión');
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Minera Norte' })).not.toBeInTheDocument());
    expect(screen.getByRole('link', { name: 'Banco Sur' })).toBeInTheDocument();
  });

  it('sin convenios explica el registro; con filtros, invita a quitarlos', async () => {
    montar('/convenios?estado=APROBADO');
    expect(await screen.findByText('Ningún convenio coincide con los filtros.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Quitar filtros' }));
    expect(await screen.findByText(/Aún no hay convenios. Las empresas cliente se registran desde el portal/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Nuevo convenio' })).not.toBeInTheDocument();
  });
});

describe('sin creación', () => {
  it('el administrador no tiene «Nuevo convenio» y la ruta no existe', async () => {
    montar('/convenios/nuevo');
    expect(await screen.findByRole('link', { name: 'Volver a los convenios' })).toBeInTheDocument();
  });
});

describe('ficha', () => {
  const abrir = async (cambios = {}) => {
    const contexto = montar('/convenios/5');
    contexto.convenios.convenios = [convenioDePrueba({ id: 5, reservas: 3, ...cambios })];
    await screen.findByRole('heading', { name: /Minera Sintética/ });
    return contexto;
  };

  it('no encontrado', async () => {
    montar('/convenios/999');
    expect(await screen.findByRole('link', { name: 'Volver a los convenios' })).toBeInTheDocument();
  });

  it('muestra los datos del registro', async () => {
    await abrir();
    expect(screen.getByText('Elena Encargada')).toBeInTheDocument();
    expect(screen.getByText('elena@minera.example')).toBeInTheDocument();
    expect(screen.getByText('Av. Apoquindo 3000, Las Condes')).toBeInTheDocument();
  });

  it('en revisión: aprobar pide confirmar', async () => {
    const { convenios } = await abrir({ estado: 'EN_REVISION', activo: false });
    await userEvent.click(screen.getByRole('button', { name: 'Aprobar' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Aprobar' }));
    expect(await screen.findByText(/Convenio aprobado/)).toBeInTheDocument();
    expect(convenios.convenios[0].estado).toBe('APROBADO');
  });

  it('en revisión: rechazar exige motivo', async () => {
    const { convenios } = await abrir({ estado: 'EN_REVISION', activo: false });
    await userEvent.click(screen.getByRole('button', { name: 'Rechazar…' }));
    await userEvent.click(screen.getByRole('button', { name: 'Rechazar' }));
    expect(screen.getByText('Indica el motivo del rechazo.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Motivo del rechazo'), 'RUT no corresponde');
    await userEvent.click(screen.getByRole('button', { name: 'Rechazar' }));
    expect(await screen.findByText(/Convenio rechazado/)).toBeInTheDocument();
    expect(convenios.cuerpos.at(-1)).toEqual({ ruta: 'POST /api/convenios/5/rechazar/', cuerpo: { motivo: 'RUT no corresponde' } });
  });

  it('aprobado: desactivar explica el corte y se puede activar de nuevo', async () => {
    await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar convenio' }));
    expect(screen.getByText(/pierde el acceso al instante/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByRole('button', { name: 'Activar convenio' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Activar convenio' }));
    await userEvent.click(screen.getByRole('button', { name: 'Activar' }));
    expect(await screen.findByRole('button', { name: 'Desactivar convenio' })).toBeInTheDocument();
  });

  it('restablecer muestra la temporal una vez', async () => {
    const { convenios } = await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }));
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }));
    const dialogo = await screen.findByRole('dialog');
    expect(within(dialogo).getByText(convenios.password)).toBeInTheDocument();
  });

  it('sin cuenta es historial: no ofrece restablecer ni reactivar', async () => {
    await abrir({ tiene_cuenta: false, encargado_email: null, estado: 'INACTIVO', activo: false });
    expect(screen.getByText(/queda como historial/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Restablecer contraseña' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Activar convenio' })).not.toBeInTheDocument();
  });

  it('una falla se informa', async () => {
    const { convenios } = await abrir();
    convenios.siguiente('POST /api/convenios/5/desactivar/', { estado: 409, cuerpo: { detail: 'El convenio está inactivo.', code: 'estado_convenio' } });
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar convenio' }));
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByText('El convenio está inactivo.')).toBeInTheDocument();
  });

  it('editar guarda los datos', async () => {
    const { convenios } = await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Editar' }));
    const nombre = screen.getByLabelText('Cliente');
    await userEvent.clear(nombre);
    await userEvent.type(nombre, 'Minera Renombrada');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument();
    expect(convenios.convenios[0].cliente_nombre).toBe('Minera Renombrada');
  });
});

describe('auditoría del convenio (HU-12, CP-24)', () => {
  const REGISTRO = { id: 1, accion: 'CREACION', usuario: 'Ana Admin', creado_en: '2026-07-15T12:00:00Z' };
  const abrirConvenio = (registros = [REGISTRO]) => {
    const contexto = montar('/convenios/5');
    contexto.convenios.convenios = [convenioDePrueba({ id: 5 })];
    contexto.convenios.auditoria = registros;
    return contexto;
  };

  it('muestra fecha, acción y usuario', async () => {
    abrirConvenio();
    const fila = (await screen.findByText('Creación')).closest('tr')!;
    expect(within(fila).getByText('Ana Admin')).toBeInTheDocument();
    expect(within(fila).getByText('mié 15-07-2026 08:00')).toBeInTheDocument();
  });

  it('una acción sin etiqueta se muestra tal cual', async () => {
    abrirConvenio([{ ...REGISTRO, accion: 'OTRA_ACCION' }]);
    expect(await screen.findByText('OTRA_ACCION')).toBeInTheDocument();
  });

  it('sin registros lo dice', async () => {
    abrirConvenio([]);
    expect(await screen.findByText('Aún no hay registros.')).toBeInTheDocument();
  });

  it('restablecer actualiza la auditoría sin recargar', async () => {
    abrirConvenio();
    await screen.findByText('Creación');
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer contraseña' }));
    await userEvent.click(screen.getByRole('button', { name: 'Restablecer' }));
    await userEvent.click(within(await screen.findByRole('dialog')).getByRole('button', { name: 'Listo' }));
    expect(await screen.findByText('Cambio de contraseña')).toBeInTheDocument();
  });

  it('pagina', async () => {
    abrirConvenio(Array.from({ length: 26 }, (_, i) => ({ ...REGISTRO, id: i + 1, accion: i === 25 ? 'EDICION' : 'CREACION' })));
    await screen.findAllByText('Creación');
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
    expect(await screen.findByText('Edición de datos')).toBeInTheDocument();
  });

  it('una falla ofrece reintentar', async () => {
    const { convenios } = montar('/convenios/5');
    convenios.convenios = [convenioDePrueba({ id: 5 })];
    convenios.siguiente('GET /api/convenios/5/auditoria/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('Aún no hay registros.')).toBeInTheDocument();
  });

  it('no ofrece modificar los registros', async () => {
    abrirConvenio();
    const tabla = await screen.findByRole('table', { name: 'Auditoría del convenio' });
    expect(within(tabla).queryByRole('button')).not.toBeInTheDocument();
  });
});
