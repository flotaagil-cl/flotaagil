/** HU-11 y HU-34: administrar convenios con autoregistro y aprobación (RN-08, RN-12). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { convenioDePrueba, ServidorConveniosFalso } from '../pruebas/servidorConveniosFalso';

const ADMIN = 'admin@andes.example';

function montar(ruta: string, email = ADMIN, servidor = new ServidorAuthFalso()) {
  const contexto = montarPanel(ruta, { email, servidor });
  const convenios = new ServidorConveniosFalso(contexto.servidor);
  return { ...contexto, convenios };
}

describe('permisos', () => {
  it('el administrador ve Convenios en el menú', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Convenios' })).toBeInTheDocument();
  });

  it('el despachador revisa: aprueba con los correos autorizados, sin editar ni ver la auditoría (DC-55)', async () => {
    const { convenios } = montar('/convenios/9', 'despacho@andes.example');
    convenios.convenios = [
      convenioDePrueba({ id: 9, estado: 'EN_REVISION', activo: false, tiene_cuenta: false, encargado_email: null, contacto_correo: 'ana@minera.example', viajes_estimados_mes: 40, correos_autorizados: ['@minera.example'] }),
    ];
    expect(await screen.findByText('ana@minera.example')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Editar' })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Aprobar' }));
    const correos = screen.getByLabelText(/Correos autorizados/);
    expect(correos).toHaveValue('@minera.example');
    await userEvent.type(correos, '{Enter}pedro@otra.example');
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Aprobar' }));
    expect(await screen.findByText(/Convenio aprobado/)).toBeInTheDocument();
    expect(convenios.convenios[0].correos_autorizados).toEqual(['@minera.example', 'pedro@otra.example']);
    expect(screen.queryByRole('button', { name: 'Desactivar convenio' })).not.toBeInTheDocument();
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

  it('muestra el tipo de acceso, enlace Ver ficha y botón Limpiar cuando hay filtros activos', async () => {
    const { convenios } = montar('/convenios');
    convenios.convenios = [
      convenioDePrueba({ id: 10, cliente_nombre: 'Minera Norte', tiene_cuenta: true }),
      convenioDePrueba({ id: 11, cliente_nombre: 'Hotel Sur', tiene_cuenta: false, estado: 'EN_REVISION', activo: false }),
    ];
    const filaNorte = (await screen.findByRole('link', { name: 'Minera Norte' })).closest('tr')!;
    const filaSur = screen.getByRole('link', { name: 'Hotel Sur' }).closest('tr')!;
    expect(within(filaNorte).getByText('Cuenta web')).toBeInTheDocument();
    expect(within(filaSur).getByText('Sin cuenta')).toBeInTheDocument();
    expect(within(filaNorte).getByRole('link', { name: 'Ver ficha' })).toHaveAttribute('href', '/convenios/10');
    expect(screen.queryByRole('button', { name: 'Limpiar' })).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Estado' }), 'En revisión');
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Minera Norte' })).not.toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: 'Limpiar' }));
    expect(await screen.findByRole('link', { name: 'Minera Norte' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Hotel Sur' })).toBeInTheDocument();
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
    expect(screen.getByText(/pierden el acceso al instante/)).toBeInTheDocument();
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

  it('cancelar la edición vuelve a la ficha sin guardar cambios', async () => {
    const { convenios } = await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Editar' }));
    const nombre = screen.getByLabelText('Cliente');
    await userEvent.clear(nombre);
    await userEvent.type(nombre, 'Cambio Descartado');
    await userEvent.click(screen.getByRole('button', { name: 'Volver' }));
    expect(screen.queryByRole('button', { name: 'Guardar' })).not.toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Editar' })).toBeInTheDocument();
    expect(convenios.convenios[0].cliente_nombre).toBe('Minera Sintética S.A.');
    expect(convenios.cuerpos).toHaveLength(0);
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
    expect(await screen.findByText('Cambio de contraseña o clave')).toBeInTheDocument();
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

describe('compartir enlace del portal (DC-73)', () => {
  it('el administrador copia la URL de registro-empresa y comparte por WhatsApp', async () => {
    const portapapeles = { writeText: vi.fn().mockResolvedValue(undefined) };
    Object.defineProperty(navigator, 'clipboard', { value: portapapeles, configurable: true });
    montar('/convenios');

    const copiar = await screen.findByRole('button', { name: 'Copiar enlace del portal' });
    const whatsapp = screen.getByRole('link', { name: 'Compartir por WhatsApp' });
    const urlEsperada = 'http://localhost:3000/solicitar/transportes-andes/registro-empresa';

    expect(whatsapp).toHaveAttribute('target', '_blank');
    expect(whatsapp).toHaveAttribute('rel', 'noreferrer');
    const href = whatsapp.getAttribute('href')!;
    expect(href).toMatch(/^https:\/\/wa\.me\/\?text=/);
    expect(decodeURIComponent(href.split('?text=')[1])).toContain(urlEsperada);

    await userEvent.click(copiar);
    expect(portapapeles.writeText).toHaveBeenCalledWith(urlEsperada);
    expect(await screen.findByRole('button', { name: 'Enlace copiado' })).toBeInTheDocument();
  });

  it('el despachador también ve los botones para compartir el enlace del portal', async () => {
    montar('/convenios', 'despacho@andes.example');
    expect(await screen.findByRole('button', { name: 'Copiar enlace del portal' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Compartir por WhatsApp' })).toBeInTheDocument();
  });

  it('sin módulo de cuentas usa la URL pública /convenio', async () => {
    const portapapeles = { writeText: vi.fn().mockResolvedValue(undefined) };
    Object.defineProperty(navigator, 'clipboard', { value: portapapeles, configurable: true });
    const servidor = new ServidorAuthFalso();
    servidor.moduloCuentas = false;
    montar('/convenios', ADMIN, servidor);

    const copiar = await screen.findByRole('button', { name: 'Copiar enlace del portal' });
    const whatsapp = screen.getByRole('link', { name: 'Compartir por WhatsApp' });
    const urlEsperada = 'http://localhost:3000/solicitar/transportes-andes/convenio';

    expect(decodeURIComponent(whatsapp.getAttribute('href')!.split('?text=')[1])).toContain(urlEsperada);
    await userEvent.click(copiar);
    expect(portapapeles.writeText).toHaveBeenCalledWith(urlEsperada);
  });

  it('si falla el portapapeles, informa que no se pudo copiar', async () => {
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText: vi.fn().mockRejectedValue(new Error('denegado')) },
      configurable: true,
    });
    montar('/convenios');
    await userEvent.click(await screen.findByRole('button', { name: 'Copiar enlace del portal' }));
    expect(await screen.findByRole('button', { name: 'No se pudo copiar' })).toBeInTheDocument();
  });
});

describe('CC-23 · clave del convenio (DC-74)', () => {
  const SIN_CUENTA = { id: 7, tiene_cuenta: false, encargado_email: null, admite_clave: true, clave_vigente: false, clave_generada_en: null };

  it('el administrador genera y revoca la clave; el panel nunca la muestra', async () => {
    const { convenios } = montar('/convenios/7');
    convenios.convenios = [convenioDePrueba(SIN_CUENTA)];
    expect(await screen.findByText(/Sin clave vigente/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Generar clave' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Generar clave' }));
    expect(await screen.findByText(/Clave generada. Se envió al correo de contacto/)).toBeInTheDocument();
    expect(screen.getByText(/Clave vigente, generada el/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Revocar clave' }));
    await userEvent.click(within(screen.getByRole('alertdialog')).getByRole('button', { name: 'Revocar' }));
    expect(await screen.findByText('Clave revocada.')).toBeInTheDocument();
    expect(screen.getByText(/Sin clave vigente/)).toBeInTheDocument();
  });

  it('el despachador no ve las acciones de la clave', async () => {
    const { convenios } = montar('/convenios/7', 'despacho@andes.example');
    convenios.convenios = [convenioDePrueba({ ...SIN_CUENTA, clave_vigente: true, clave_generada_en: '2026-11-20T12:00:00Z' })];
    await screen.findByRole('heading', { name: /Minera Sintética/ });
    expect(screen.queryByRole('button', { name: /Regenerar clave|Generar clave/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Revocar clave' })).not.toBeInTheDocument();
  });
});
