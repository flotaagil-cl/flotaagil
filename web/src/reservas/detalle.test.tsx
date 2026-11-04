/** Detalle con historial y cancelación con motivo (CP-06). */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { MENSAJES } from '../api/errores';
import { ESPERA_RESPUESTA_MS } from './api';
import { esperarListado, montarPanel } from '../pruebas/montar';
import { viajeDePrueba } from '../pruebas/servidorViajesFalso';
import type { components } from '../api/esquema';

type Candidato = components['schemas']['Candidato'];

async function abrirDetalle(viaje = viajeDePrueba({ id: 8 })) {
  const contexto = montarPanel(`/reservas/${viaje.id}`);
  contexto.viajes.agregar(viaje);
  await screen.findByRole('heading', { name: new RegExp(`Reserva #${viaje.id}`) });
  return contexto;
}

describe('detalle', () => {
  it('muestra los datos en hora de Santiago y el historial en orden', async () => {
    await abrirDetalle(
      viajeDePrueba({
        id: 8,
        estado: 'ASIGNADO',
        sentido: 'DESDE_AEROPUERTO',
        recogida_en: '2026-07-15T14:00:00Z',
        conductor: { id: 3, nombre: 'Carla Conductora' },
        vehiculo: { id: 4, patente: 'ABCD12' },
        vuelo: { numero: 'LA123', fecha: '2026-07-15', hora_programada: '2026-07-15T13:30:00Z', hora_estimada: '2026-07-15T13:50:00Z', estado_vuelo: 'DEMORADO' },
        historial: [
          { estado_anterior: 'SOLICITADO', estado_nuevo: 'ASIGNADO', actor: 'SISTEMA', usuario: '', creado_en: '2026-07-15T12:01:00Z' },
          { estado_anterior: null, estado_nuevo: 'SOLICITADO', actor: 'DESPACHADOR', usuario: 'Diego Despacho', creado_en: '2026-07-15T12:00:00Z' },
        ],
      }),
    );
    expect(screen.getByRole('heading', { name: 'Reserva #8 Asignado' })).toBeInTheDocument();
    expect(screen.getByText('mié 15-07-2026 10:00')).toBeInTheDocument();
    expect(screen.getByText(/LA123 · llegada programada mié 15-07-2026 09:30 · estimada mié 15-07-2026 09:50 · Demorado/)).toBeInTheDocument();
    expect(screen.getByText('Carla Conductora · ABCD12')).toBeInTheDocument();
    const pasos = within(screen.getByRole('list', { name: 'Historial de estados' })).getAllByRole('listitem');
    expect(pasos.map((p) => p.textContent)).toEqual([
      'Solicitadomié 15-07-2026 08:00 · Despachador · Diego Despacho',
      'Solicitado → Asignadomié 15-07-2026 08:01 · Sistema',
    ]);
    // ASIGNADO: ni editar ni cancelar, con la explicación.
    expect(screen.queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Cancelar reserva…' })).not.toBeInTheDocument();
    expect(screen.getByText('No se puede editar ni cancelar mientras se espera la respuesta del conductor.')).toBeInTheDocument();
  });

  it.each([
    ['SOLICITADO', true, true, null],
    ['EN_CAMINO', false, true, 'Ya fue despachada: se puede cancelar, pero no editar.'],
    ['FINALIZADO', false, false, 'La reserva está cerrada.'],
    ['PASAJERO_A_BORDO', false, false, 'Con el pasajero a bordo solo se puede forzar el cierre o la anulación, si el conductor no puede hacerlo.'],
  ] as const)('%s: editar %s, cancelar %s', async (estado, editar, cancelar, explicacion) => {
    await abrirDetalle(viajeDePrueba({ id: 9, estado }));
    expect(Boolean(screen.queryByRole('link', { name: 'Editar' }))).toBe(editar);
    expect(Boolean(screen.queryByRole('button', { name: 'Cancelar reserva…' }))).toBe(cancelar);
    if (explicacion) expect(screen.getByText(explicacion)).toBeInTheDocument();
  });

  it('el historial distingue la llegada manual y su distancia (DC-20)', async () => {
    const paso = (distancia_m: number | null) => ({
      estado_anterior: 'EN_CAMINO' as const,
      estado_nuevo: 'EN_ZONA' as const,
      actor: 'CONDUCTOR' as const,
      usuario: 'Carla Conductora',
      manual: true,
      distancia_m,
      creado_en: '2026-07-15T12:01:00Z',
    });
    await abrirDetalle(viajeDePrueba({ id: 12, estado: 'EN_ZONA', historial: [paso(1320), paso(null)] }));
    expect(screen.getByText(/Indicado a mano, sin geocerca · a 1\.320 m del origen/)).toBeInTheDocument();
    expect(screen.getByText(/Indicado a mano, sin geocerca · sin posición GPS desde que salió/)).toBeInTheDocument();
  });

  it('una llegada por geocerca no muestra esa marca', async () => {
    await abrirDetalle(viajeDePrueba({ id: 13, estado: 'EN_ZONA' }));
    expect(screen.queryByText(/Indicado a mano/)).not.toBeInTheDocument();
  });

  it('muestra la calificación solo si el pasajero respondió (RN-14)', async () => {
    await abrirDetalle(viajeDePrueba({ id: 10, estado: 'FINALIZADO', calificacion: 4 }));
    expect(screen.getByText('4 de 5')).toBeInTheDocument();
  });

  it('sin calificación no muestra esa fila', async () => {
    await abrirDetalle(viajeDePrueba({ id: 11, estado: 'FINALIZADO' }));
    expect(screen.queryByText('Calificación')).not.toBeInTheDocument();
  });

  it('una cancelada muestra el motivo y quién la canceló', async () => {
    await abrirDetalle(viajeDePrueba({ id: 10, estado: 'CANCELADO', motivo_cancelacion: 'El pasajero no viaja.', origen_cancelacion: 'PASAJERO' }));
    expect(screen.getByText('El pasajero no viaja. (Pasajero)')).toBeInTheDocument();
  });

  it('404 (no existe o es de otra empresa): «Reserva no encontrada»', async () => {
    montarPanel('/reservas/999');
    expect(await screen.findByRole('heading', { name: 'Reserva no encontrada' })).toBeInTheDocument();
  });

  it('un error de red ofrece Reintentar', async () => {
    const { servidor, viajes } = montarPanel('/reservas/11');
    viajes.agregar(viajeDePrueba({ id: 11 }));
    servidor.fallar('GET /api/viajes/11/', 'red');
    expect(await screen.findByText(MENSAJES.sin_conexion)).toBeInTheDocument();
    servidor.reparar();
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('heading', { name: /Reserva #11/ })).toBeInTheDocument();
  });
});

describe('cancelar con motivo (CP-06)', () => {
  it('el motivo es obligatorio: sin motivo no se envía', async () => {
    const { viajes } = await abrirDetalle();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar reserva…' }));
    const dialogo = screen.getByRole('dialog', { name: 'Cancelar la reserva #8' });
    await userEvent.type(within(dialogo).getByLabelText('Motivo'), '   ');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cancelar reserva' }));
    expect(await within(dialogo).findByText('Indica el motivo de la cancelación.')).toBeInTheDocument();
    expect(viajes.cuerpos).toEqual([]);
  });

  it('confirmar cancela: estado, motivo e historial actualizados', async () => {
    const { viajes } = await abrirDetalle();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar reserva…' }));
    const dialogo = screen.getByRole('dialog');
    await userEvent.type(within(dialogo).getByLabelText('Motivo'), ' El pasajero no viaja. ');
    expect(within(dialogo).getByText('23/200')).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cancelar reserva' }));
    expect(await screen.findByText('Reserva cancelada.')).toBeInTheDocument();
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(viajes.cuerpos).toEqual([{ ruta: 'POST /api/viajes/8/cancelar/', cuerpo: { motivo: 'El pasajero no viaja.' } }]);
    expect(screen.getByRole('heading', { name: 'Reserva #8 Cancelado' })).toBeInTheDocument();
    expect(screen.getByText('El pasajero no viaja. (Despachador)')).toBeInTheDocument();
    expect(screen.getByText(/Solicitado → Cancelado/)).toBeInTheDocument();
  });

  it('«Volver» cierra sin cancelar; con conductor asignado lo advierte', async () => {
    const { viajes } = await abrirDetalle(viajeDePrueba({ id: 12, estado: 'EN_CAMINO', conductor: { id: 3, nombre: 'Carla Conductora' } }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar reserva…' }));
    expect(screen.getByText('El conductor Carla Conductora ya está asignado a esta reserva.')).toBeInTheDocument();
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Volver' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(viajes.cuerpos).toEqual([]);
  });

  it('409: la reserva ya no se puede cancelar; se muestra el motivo y el estado real', async () => {
    const { viajes } = await abrirDetalle();
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar reserva…' }));
    viajes.cambiarEstado(8, 'FINALIZADO');
    const dialogo = screen.getByRole('dialog');
    await userEvent.type(within(dialogo).getByLabelText('Motivo'), 'Duplicada');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cancelar reserva' }));
    expect(await within(dialogo).findByText('Una reserva en estado FINALIZADO no se puede cancelar desde aquí.')).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Volver' }));
    // El detalle se recargó (invalidación) y ya no ofrece cancelar.
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Reserva #8 Finalizado' })).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Cancelar reserva…' })).not.toBeInTheDocument();
  });

  it('después de cancelar, el listado se vuelve a consultar y muestra el estado nuevo', async () => {
    const { viajes, router } = montarPanel('/reservas?desde=');
    viajes.agregar(viajeDePrueba({ id: 13, pasajero: { id: 1, nombre: 'Rita Ruiz', telefono: '+56900000002' } }));
    await esperarListado();
    expect(screen.getByRole('row', { name: /Rita Ruiz/ })).toHaveTextContent('Solicitado');
    await userEvent.click(within(screen.getByRole('row', { name: /Rita Ruiz/ })).getByRole('link'));
    await userEvent.click(await screen.findByRole('button', { name: 'Cancelar reserva…' }));
    await userEvent.type(within(screen.getByRole('dialog')).getByLabelText('Motivo'), 'Duplicada');
    await userEvent.click(within(screen.getByRole('dialog')).getByRole('button', { name: 'Cancelar reserva' }));
    await screen.findByText('Reserva cancelada.');
    await router.navigate(-1);
    await waitFor(() => expect(screen.getByRole('row', { name: /Rita Ruiz/ })).toHaveTextContent('Cancelado'));
  });
});

describe('vuelo verificado (HU-26)', () => {
  it('indica si el vuelo se verificó con la API de vuelos', async () => {
    const vuelo = { numero: 'LA123', fecha: '2026-07-15', hora_programada: '2026-07-15T13:30:00Z', hora_estimada: null, estado_vuelo: 'PROGRAMADO' as const };
    await abrirDetalle(viajeDePrueba({ id: 8, sentido: 'DESDE_AEROPUERTO', vuelo: { ...vuelo, ultima_consulta_en: '2026-07-15T10:00:00Z' } }));
    expect(screen.getByText('Verificado con la API de vuelos el mié 15-07-2026 06:00')).toBeInTheDocument();
  });

  it('o si quedó sin verificar', async () => {
    const vuelo = { numero: 'LA123', fecha: '2026-07-15', hora_programada: '2026-07-15T13:30:00Z', hora_estimada: null, estado_vuelo: 'PROGRAMADO' as const, ultima_consulta_en: null };
    await abrirDetalle(viajeDePrueba({ id: 9, sentido: 'DESDE_AEROPUERTO', vuelo }));
    expect(screen.getByText('Sin verificar: la API de vuelos no respondió al registrarlo')).toBeInTheDocument();
  });
});

describe('asignar conductor (HU-14)', () => {
  const candidato = (id: number, nombre: string, cambios: Partial<Candidato> = {}): Candidato => ({
    id,
    nombre,
    patente: `BCDF${id}0`,
    distancia_m: 850,
    posicion_en: '2026-11-03T15:00:00Z',
    confiable: true,
    ultimo_viaje_en: null,
    posicion_fila: null,
    sugerido: false,
    ...cambios,
  });

  async function abrirDialogo(candidatos: Candidato[]) {
    const contexto = await abrirDetalle(viajeDePrueba({ id: 8, estado: 'SOLICITADO' }));
    contexto.viajes.candidatos = candidatos;
    await userEvent.click(screen.getByRole('button', { name: 'Asignar conductor…' }));
    return { contexto, dialogo: await screen.findByRole('dialog', { name: 'Asignar la reserva #8' }) };
  }

  it('propone al sugerido, con distancia y último viaje, y asigna al confirmar', async () => {
    const { dialogo } = await abrirDialogo([
      candidato(3, 'Carla Conductora', { sugerido: true, ultimo_viaje_en: '2026-07-15T14:00:00Z' }),
      candidato(4, 'Pedro Soto', { distancia_m: 4200 }),
    ]);
    const sugerido = await within(dialogo).findByRole('list', { name: 'Conductor sugerido' });
    expect(sugerido.textContent).toContain('Sugerido: Carla Conductora');
    expect(sugerido.textContent).toContain('a 850 m del origen');
    expect(sugerido.textContent).toContain('último viaje mié 15-07-2026 10:00');
    // Abrir el diálogo no asigna nada (RN-02).
    expect(screen.getByRole('heading', { name: 'Reserva #8 Solicitado' })).toBeInTheDocument();
    await userEvent.click(within(sugerido).getByRole('button', { name: 'Asignar a Carla Conductora' }));
    expect(await screen.findByText('Reserva asignada a Carla Conductora. Esperando que acepte en la app (60 s).')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Reserva #8 Asignado' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Asignar conductor…' })).not.toBeInTheDocument();
  });

  it('el desplegable ofrece al resto de los disponibles', async () => {
    const { dialogo } = await abrirDialogo([
      candidato(3, 'Carla Conductora', { sugerido: true }),
      candidato(4, 'Pedro Soto', { distancia_m: 4200 }),
      candidato(5, 'Ana Ríos', { distancia_m: null, posicion_en: null, confiable: false }),
    ]);
    const desplegable = await within(dialogo).findByRole('combobox', { name: 'Otro conductor disponible' });
    expect(within(desplegable).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Elige un conductor…',
      'Pedro Soto · BCDF40 · a 4,2 km',
      'Ana Ríos · BCDF50 · sin posición (no reciente)',
    ]);
    const asignarElegido = within(dialogo).getByRole('button', { name: 'Asignar al elegido' });
    expect(asignarElegido).toBeDisabled();
    await userEvent.selectOptions(desplegable, 'Pedro Soto · BCDF40 · a 4,2 km');
    await userEvent.click(asignarElegido);
    expect(await screen.findByText('Reserva asignada a Pedro Soto. Esperando que acepte en la app (60 s).')).toBeInTheDocument();
  });

  it('en el aeropuerto propone al primero de la fila (HU-29)', async () => {
    const contexto = await abrirDetalle(viajeDePrueba({ id: 8, estado: 'SOLICITADO', sentido: 'DESDE_AEROPUERTO' }));
    contexto.viajes.candidatos = [
      candidato(3, 'Carla Conductora', { sugerido: true, posicion_fila: 1 }),
      candidato(4, 'Pedro Soto', { posicion_fila: 2, distancia_m: 100 }),
    ];
    await userEvent.click(screen.getByRole('button', { name: 'Asignar conductor…' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Asignar la reserva #8' });
    expect((await within(dialogo).findByRole('list', { name: 'Conductor sugerido' })).textContent).toContain('Primero de la fila del aeropuerto');
    expect(within(dialogo).getByRole('option', { name: /Pedro Soto · BCDF40 · fila 2/ })).toBeInTheDocument();
  });

  it('en el aeropuerto sin fila lo explica', async () => {
    const contexto = await abrirDetalle(viajeDePrueba({ id: 8, estado: 'SOLICITADO', sentido: 'DESDE_AEROPUERTO' }));
    contexto.viajes.candidatos = [candidato(4, 'Pedro Soto')];
    await userEvent.click(screen.getByRole('button', { name: 'Asignar conductor…' }));
    expect(await screen.findByText(/no hay conductores en la fila del aeropuerto/)).toBeInTheDocument();
  });

  it('sin sugerencia lo explica y deja elegir', async () => {
    const { dialogo } = await abrirDialogo([candidato(5, 'Ana Ríos', { confiable: false })]);
    expect(await within(dialogo).findByText(/Sin sugerencia: ningún conductor tiene una posición reciente/)).toBeInTheDocument();
    expect(within(dialogo).getByRole('combobox', { name: 'Conductor disponible' })).toBeInTheDocument();
  });

  it('un 409 se muestra en el diálogo', async () => {
    const { contexto } = await abrirDialogo([candidato(3, 'Carla Conductora', { sugerido: true })]);
    contexto.viajes.siguiente('POST /api/viajes/8/asignar/', {
      estado: 409,
      cuerpo: { detail: 'Carla Conductora ya tiene un viaje en ejecución (RN-03).', code: 'asignacion_no_permitida' },
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Asignar a Carla Conductora' }));
    expect(await screen.findByText('Carla Conductora ya tiene un viaje en ejecución (RN-03).')).toBeInTheDocument();
  });

  it('sin disponibles lo dice', async () => {
    await abrirDetalle(viajeDePrueba({ id: 8, estado: 'SOLICITADO' }));
    await userEvent.click(screen.getByRole('button', { name: 'Asignar conductor…' }));
    expect(await screen.findByText('No hay conductores Disponibles sin viaje en este momento.')).toBeInTheDocument();
  });

  it('solo en reservas solicitadas', async () => {
    await abrirDetalle(viajeDePrueba({ id: 8, estado: 'PENDIENTE_CONFIRMACION' }));
    expect(screen.queryByRole('button', { name: 'Asignar conductor…' })).not.toBeInTheDocument();
  });
});

describe('cierre o anulación forzada (HU-05)', () => {
  const aBordo = () => viajeDePrueba({ id: 8, estado: 'PASAJERO_A_BORDO', tarifa: 15000, conductor: { id: 3, nombre: 'Carla Conductora' } });
  const abrir = async () => {
    const contexto = await abrirDetalle(aBordo());
    await userEvent.click(screen.getByRole('button', { name: 'Forzar cierre o anulación…' }));
    return { contexto, dialogo: await screen.findByRole('dialog', { name: /Cierre o anulación forzada/ }) };
  };

  it.each(['SOLICITADO', 'EN_CAMINO', 'EN_ZONA', 'FINALIZADO'] as const)('en %s no se ofrece', async (estado) => {
    await abrirDetalle(viajeDePrueba({ id: 9, estado }));
    expect(screen.queryByRole('button', { name: 'Forzar cierre o anulación…' })).not.toBeInTheDocument();
  });

  it('cerrar exige motivo y método, y precarga la tarifa', async () => {
    const { contexto, dialogo } = await abrir();
    expect(within(dialogo).getByRole('textbox', { name: 'Monto cobrado (CLP)' })).toHaveValue('15000');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar viaje' }));
    expect(await within(dialogo).findByText('Indica el motivo.')).toBeInTheDocument();
    expect(within(dialogo).getByText('Elige el método de pago.')).toBeInTheDocument();
    expect(contexto.viajes.cuerpos).toEqual([]);
  });

  it.each([
    ['', 'Ingresa el monto cobrado, en pesos enteros.'],
    ['15000,5', 'Ingresa el monto cobrado, en pesos enteros.'],
    ['600.000', 'El monto máximo es $500.000.'],
  ])('monto «%s»: %s', async (monto, mensaje) => {
    const { dialogo } = await abrir();
    const campo = within(dialogo).getByRole('textbox', { name: 'Monto cobrado (CLP)' });
    await userEvent.clear(campo);
    if (monto) await userEvent.type(campo, monto);
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar viaje' }));
    expect(await within(dialogo).findByText(mensaje)).toBeInTheDocument();
  });

  it('cerrar envía motivo, método y monto, y muestra el responsable', async () => {
    const { contexto, dialogo } = await abrir();
    await userEvent.type(within(dialogo).getByRole('textbox', { name: 'Motivo' }), 'Sin señal');
    await userEvent.selectOptions(within(dialogo).getByRole('combobox', { name: 'Método de pago' }), 'Tarjeta');
    const monto = within(dialogo).getByRole('textbox', { name: 'Monto cobrado (CLP)' });
    await userEvent.clear(monto);
    await userEvent.type(monto, '18.500');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Cerrar viaje' }));
    expect(await screen.findByText('Viaje cerrado con su pago.')).toBeInTheDocument();
    expect(contexto.viajes.cuerpos.at(-1)?.cuerpo).toEqual({ accion: 'CERRAR', motivo: 'Sin señal', metodo: 'TARJETA', monto: 18500 });
    expect(screen.getByText('Cierre forzado')).toBeInTheDocument();
    expect(screen.getByText(/Diego Despacho · /)).toBeInTheDocument();
  });

  it('anular solo pide motivo', async () => {
    const { contexto, dialogo } = await abrir();
    await userEvent.click(within(dialogo).getByRole('radio', { name: /Anular/ }));
    expect(within(dialogo).queryByRole('combobox', { name: 'Método de pago' })).not.toBeInTheDocument();
    await userEvent.type(within(dialogo).getByRole('textbox', { name: 'Motivo' }), 'No se completó');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Anular viaje' }));
    expect(await screen.findByText('Viaje anulado.')).toBeInTheDocument();
    expect(contexto.viajes.cuerpos.at(-1)?.cuerpo).toEqual({ accion: 'ANULAR', motivo: 'No se completó' });
  });

  it('un 409 se muestra en el diálogo', async () => {
    const { contexto, dialogo } = await abrir();
    contexto.viajes.siguiente('POST /api/viajes/8/forzar-cierre/', {
      estado: 409,
      cuerpo: { detail: 'Solo se fuerza con el pasajero a bordo.', code: 'conflicto_estado' },
    });
    await userEvent.click(within(dialogo).getByRole('radio', { name: /Anular/ }));
    await userEvent.type(within(dialogo).getByRole('textbox', { name: 'Motivo' }), 'x');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Anular viaje' }));
    expect(await within(dialogo).findByText('Solo se fuerza con el pasajero a bordo.')).toBeInTheDocument();
  });

  it('solo ofrece Convenio en viajes de convenio', async () => {
    const { dialogo } = await abrir();
    expect(within(dialogo).queryByRole('option', { name: 'Convenio' })).not.toBeInTheDocument();
  });
});

describe('nueva hora de recogida (HU-27)', () => {
  const VUELO = {
    numero: 'LA845',
    fecha: '2026-07-15',
    hora_programada: '2026-07-15T13:30:00Z',
    hora_estimada: '2026-07-15T14:10:00Z',
    estado_vuelo: 'DEMORADO' as const,
    recogida_propuesta: '2026-07-15T14:30:00Z',
    propuesta_en: '2026-07-15T12:00:00Z',
  };
  const conPropuesta = () => viajeDePrueba({ id: 8, recogida_en: '2026-07-15T13:50:00Z', vuelo: VUELO });

  it('muestra la propuesta sin cambiar la recogida (RN-02)', async () => {
    await abrirDetalle(conPropuesta());
    const propuesta = screen.getByRole('region', { name: 'Cambió la llegada del vuelo' });
    expect(propuesta.textContent).toContain('ahora llega mié 15-07-2026 10:10');
    expect(propuesta.textContent).toContain('propuesta: mié 15-07-2026 10:30');
    expect(propuesta.textContent).toContain('actual: mié 15-07-2026 09:50');
    expect(screen.getByText('mié 15-07-2026 09:50', { selector: 'dd' })).toBeInTheDocument();
  });

  it('al confirmar cambia la recogida y envía la hora que se vio', async () => {
    const contexto = await abrirDetalle(conPropuesta());
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar nueva hora' }));
    expect(await screen.findByText('mié 15-07-2026 10:30', { selector: 'dd' })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: 'Cambió la llegada del vuelo' })).not.toBeInTheDocument();
    expect(contexto.viajes.cuerpos.at(-1)?.cuerpo).toEqual({ recogida_propuesta: '2026-07-15T14:30:00Z' });
  });

  it('al descartar mantiene la recogida', async () => {
    await abrirDetalle(conPropuesta());
    await userEvent.click(screen.getByRole('button', { name: 'Mantener la hora actual' }));
    await waitFor(() => expect(screen.queryByRole('region', { name: 'Cambió la llegada del vuelo' })).not.toBeInTheDocument());
    expect(screen.getByText('mié 15-07-2026 09:50', { selector: 'dd' })).toBeInTheDocument();
  });

  it('si la propuesta cambió mientras se miraba, avisa', async () => {
    const contexto = await abrirDetalle(conPropuesta());
    contexto.viajes.siguiente('POST /api/viajes/8/confirmar-recogida/', {
      estado: 409,
      cuerpo: { detail: 'La propuesta cambió o ya se resolvió. Revisa la hora actual.', code: 'propuesta_no_vigente' },
    });
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar nueva hora' }));
    expect(await screen.findByText('La propuesta cambió o ya se resolvió. Revisa la hora actual.')).toBeInTheDocument();
  });

  it('sin propuesta no muestra nada', async () => {
    await abrirDetalle(viajeDePrueba({ id: 9, vuelo: { ...VUELO, recogida_propuesta: null, propuesta_en: null } }));
    expect(screen.queryByRole('region', { name: 'Cambió la llegada del vuelo' })).not.toBeInTheDocument();
  });
});

describe('esperando la respuesta del conductor (HU-15)', () => {
  it('la ficha de una reserva asignada se actualiza sola', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const contexto = await abrirDetalle(viajeDePrueba({ id: 8, estado: 'ASIGNADO', conductor: { id: 3, nombre: 'Carla Conductora' } }));
    contexto.viajes.cambiarEstado(8, 'ACEPTADO');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ESPERA_RESPUESTA_MS);
    });
    expect(await screen.findByRole('heading', { name: 'Reserva #8 Aceptado' })).toBeInTheDocument();
    vi.useRealTimers();
  });
});
