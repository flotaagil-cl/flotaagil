/** HU-11: administrar convenios con link y contraseña (CP-22, RN-08). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
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
      convenioDePrueba({ id: 2, cliente_nombre: 'Banco Sur', activo: false, reservas: 0 }),
    ];
    const enlace = await screen.findByRole('link', { name: 'Minera Norte' });
    const fila = enlace.closest('tr')!;
    expect(within(fila).getByText('1.234')).toBeInTheDocument();
    expect(within(fila).getByText('Activo')).toBeInTheDocument();
    expect(screen.getByText('Inactivo')).toBeInTheDocument();
    expect(screen.getByText('2 convenios')).toBeInTheDocument();
  });

  it('filtra por estado', async () => {
    const { convenios } = montar('/convenios');
    convenios.convenios = [convenioDePrueba({ cliente_nombre: 'Minera Norte' }), convenioDePrueba({ cliente_nombre: 'Banco Sur', activo: false })];
    await screen.findByRole('link', { name: 'Banco Sur' });
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Estado' }), 'Activos');
    await waitFor(() => expect(screen.queryByRole('link', { name: 'Banco Sur' })).not.toBeInTheDocument());
    expect(screen.getByRole('link', { name: 'Minera Norte' })).toBeInTheDocument();
  });

  it('sin convenios invita a crear; con filtros, a quitarlos', async () => {
    montar('/convenios?activo=true');
    expect(await screen.findByText('Ningún convenio coincide con los filtros.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Quitar filtros' }));
    expect(await screen.findByText('Aún no hay convenios.')).toBeInTheDocument();
  });
});

describe('crear', () => {
  it('valida antes de enviar', async () => {
    const { convenios } = montar('/convenios/nuevo');
    await userEvent.click(await screen.findByRole('button', { name: 'Crear convenio' }));
    expect(await screen.findByText('Ingresa el nombre del cliente.')).toBeInTheDocument();
    expect(screen.getByText(/RUT inválido/)).toBeInTheDocument();
    expect(convenios.cuerpos).toEqual([]);
  });

  it('normaliza, muestra la contraseña una sola vez y abre la ficha con su link', async () => {
    const { convenios, router } = montar('/convenios/nuevo');
    await userEvent.type(await screen.findByRole('textbox', { name: 'Cliente' }), ' Minera Norte ');
    await userEvent.type(screen.getByRole('textbox', { name: 'RUT' }), '76.543.210-3');
    await userEvent.click(screen.getByRole('button', { name: 'Crear convenio' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Contraseña del convenio' });
    expect(within(dialogo).getByLabelText('Contraseña del convenio').textContent).toBe('ClaveSintetica23');
    expect(convenios.cuerpos[0].cuerpo).toEqual({ cliente_nombre: 'Minera Norte', cliente_rut: '76543210-3' });
    expect(screen.getByLabelText('Link del convenio').textContent).toContain('/convenio/tokenSintetico');
    // La contraseña no queda en la URL ni en el historial.
    expect(router.state.location.search).toBe('');
    await waitFor(() => expect(router.state.location.state).toBeNull());
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Listo' }));
    expect(screen.queryByText('ClaveSintetica23')).not.toBeInTheDocument();
  });

  it('un error del servidor queda en su campo', async () => {
    const { convenios } = montar('/convenios/nuevo');
    convenios.siguiente('POST /api/convenios/', { estado: 400, cuerpo: { cliente_rut: ['El dígito verificador del RUT no es válido.'] } });
    await userEvent.type(await screen.findByRole('textbox', { name: 'Cliente' }), 'Minera');
    await userEvent.type(screen.getByRole('textbox', { name: 'RUT' }), '76543210-3');
    await userEvent.click(screen.getByRole('button', { name: 'Crear convenio' }));
    expect(await screen.findByText('El dígito verificador del RUT no es válido.')).toBeInTheDocument();
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

  it('rotar pide confirmar y muestra la nueva', async () => {
    await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Rotar contraseña' }));
    expect(screen.getByText(/la actual dejará de servir/)).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Rotar' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Contraseña del convenio' });
    expect(within(dialogo).getByLabelText('Contraseña del convenio').textContent).toBe('ClaveSintetica23N');
  });

  it('cancelar la confirmación no hace nada', async () => {
    const { convenios } = await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar convenio' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));
    expect(convenios.convenios[0].activo).toBe(true);
    expect(convenios.cuerpos).toEqual([]);
  });

  it('desactivar explica que no borra el historial y marca el link', async () => {
    const { convenios } = await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar convenio' }));
    expect(screen.getByText(/Las reservas ya hechas no se borran ni se cancelan/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Desactivar' }));
    expect(await screen.findByText('Convenio desactivado: su link dejó de funcionar.')).toBeInTheDocument();
    expect(screen.getByText(/este link no funciona/)).toBeInTheDocument();
    expect(convenios.cuerpos[0].cuerpo).toEqual({ activo: false });
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('se puede activar de nuevo', async () => {
    await abrir({ activo: false });
    await userEvent.click(screen.getByRole('button', { name: 'Activar convenio' }));
    await userEvent.click(screen.getByRole('button', { name: 'Activar' }));
    expect(await screen.findByText('Convenio activado: su link vuelve a funcionar.')).toBeInTheDocument();
  });

  it('una falla se informa', async () => {
    const { convenios } = await abrir();
    convenios.siguiente('POST /api/convenios/5/rotar-password/', { estado: 500, cuerpo: {} });
    await userEvent.click(screen.getByRole('button', { name: 'Rotar contraseña' }));
    await userEvent.click(screen.getByRole('button', { name: 'Rotar' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('editar guarda los datos', async () => {
    const { convenios } = await abrir();
    await userEvent.click(screen.getByRole('button', { name: 'Editar' }));
    const nombre = screen.getByRole('textbox', { name: 'Cliente' });
    await userEvent.clear(nombre);
    await userEvent.type(nombre, 'Minera Nueva');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument();
    expect(convenios.convenios[0].cliente_nombre).toBe('Minera Nueva');
  });

  it('copia el link', async () => {
    await abrir();
    const escribir = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: escribir }, configurable: true });
    await userEvent.click(screen.getByRole('button', { name: 'Copiar link' }));
    await waitFor(() => expect(escribir).toHaveBeenCalledWith(expect.stringContaining('/convenio/tokenSintetico')));
    expect(await screen.findByText('Link copiado.')).toBeInTheDocument();
  });

  it('si no se puede copiar lo dice', async () => {
    await abrir();
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: vi.fn().mockRejectedValue(new Error('no')) }, configurable: true });
    await userEvent.click(screen.getByRole('button', { name: 'Copiar link' }));
    expect(await screen.findByText(/No se pudo copiar/)).toBeInTheDocument();
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

  it('rotar actualiza la auditoría sin recargar', async () => {
    abrirConvenio();
    await screen.findByText('Creación');
    await userEvent.click(screen.getByRole('button', { name: 'Rotar contraseña' }));
    await userEvent.click(screen.getByRole('button', { name: 'Rotar' }));
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
