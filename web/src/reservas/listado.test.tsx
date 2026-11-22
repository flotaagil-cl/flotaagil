import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { MENSAJES } from '../api/errores';
import { aIso, hoy, inicioDelDia } from '../hora/hora';
import { consultasDelListado, esperarListado, montarPanel } from '../pruebas/montar';
import type { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { viajeDePrueba } from '../pruebas/servidorViajesFalso';

/** Query de la última petición al listado, como lista de pares (estado puede repetirse). */
function ultimaConsulta(servidor: ServidorAuthFalso): [string, string][] {
  const url = consultasDelListado(servidor).at(-1)!;
  return [...new URLSearchParams(url.split('?')[1] ?? '').entries()];
}

const HOY_00 = () => aIso(inicioDelDia(hoy()));

describe('listado de reservas', () => {
  it('vista por defecto: «desde hoy 00:00» visible y aplicado; filas con la hora en Santiago', async () => {
    const { servidor, viajes } = montarPanel('/reservas');
    viajes.agregar(viajeDePrueba({ id: 7, recogida_en: '2026-04-05T03:30:00Z', pasajero: { id: 1, nombre: 'Rita Ruiz', telefono: '+56900000002' } }));
    await esperarListado();
    expect(screen.getByRole('list', { name: 'Filtros activos' })).toHaveTextContent('Desde hoy 00:00');
    expect(ultimaConsulta(servidor)).toEqual([['desde', HOY_00()]]);
    const fila = screen.getByRole('row', { name: /Rita Ruiz/ });
    // La hora repetida de abril se muestra con su desfase.
    expect(within(fila).getByRole('link', { name: 'sáb 04-04-2026 23:30 (UTC−4)' })).toHaveAttribute('href', '/reservas/7');
    expect(fila).toHaveTextContent('Solicitado');
    expect(screen.getByText(/1 reserva · página 1 de 1/)).toBeInTheDocument();
  });

  it('HU-69: bajo la reserva de aeropuerto va la línea de vuelo; la urbana no la tiene', async () => {
    const { viajes } = montarPanel('/reservas');
    const en = (min: number) => new Date(Date.now() + min * 60_000).toISOString();
    viajes.agregar(
      viajeDePrueba({ id: 7, pasajero: { id: 1, nombre: 'Rita Ruiz', telefono: '+56900000002' } }),
      viajeDePrueba({
        id: 8,
        sentido: 'DESDE_AEROPUERTO',
        recogida_en: en(100),
        vuelo: {
          numero: 'LA845',
          fecha: '2026-11-18',
          hora_programada: en(80),
          hora_estimada: null,
          estado_vuelo: 'PROGRAMADO',
          ultima_consulta_en: en(-5),
          recogida_propuesta: null,
          internacional: null,
          margen_min: 20,
          recogida_sugerida: en(100),
        },
      }),
    );
    await esperarListado();
    const linea = screen.getByRole('row', { name: 'Vuelo de la reserva 8' });
    expect(linea).toHaveTextContent(/Vuelo asociado LA845 · aterriza a las \d\d:\d\d/);
    expect(linea).toHaveTextContent('a tiempo');
    expect(linea).toHaveTextContent('en 1 h 20 min');
    expect(screen.queryByRole('row', { name: 'Vuelo de la reserva 7' })).not.toBeInTheDocument();
  });

  it('quitar «desde hoy» deja `desde=` en la URL y no se aplica', async () => {
    const { servidor, router } = montarPanel('/reservas');
    await esperarListado();
    await userEvent.click(screen.getByRole('button', { name: 'Quitar filtro Desde hoy 00:00' }));
    await waitFor(() => expect(router.state.location.search).toBe('?desde='));
    await waitFor(() => expect(ultimaConsulta(servidor)).toEqual([]));
  });

  it('los filtros de la URL van a la API y sobreviven a F5', async () => {
    const url =
      '/reservas?estado=PENDIENTE_CONFIRMACION&estado=SOLICITADO&desde=2026-07-15T10%3A00&sentido=DESDE_AEROPUERTO&canal=WHATSAPP&q=r%C3%ADa&ordenar=-creado_en';
    const { servidor, recargar } = montarPanel(url);
    await esperarListado();
    const esperada = [
      ['estado', 'PENDIENTE_CONFIRMACION'],
      ['estado', 'SOLICITADO'],
      ['desde', '2026-07-15T14:00:00.000Z'],
      ['sentido', 'DESDE_AEROPUERTO'],
      ['canal', 'WHATSAPP'],
      ['q', 'ría'],
      ['ordenar', '-creado_en'],
    ];
    expect(ultimaConsulta(servidor)).toEqual(esperada);
    expect(screen.getByRole('combobox', { name: 'Sentido' })).toHaveValue('DESDE_AEROPUERTO');
    expect(screen.getByRole('searchbox', { name: 'Buscar' })).toHaveValue('ría');

    const { router } = recargar();
    await esperarListado();
    expect(router.state.location.search).toBe(url.slice('/reservas'.length));
    expect(ultimaConsulta(servidor)).toEqual(esperada);
    expect(screen.getByRole('list', { name: 'Filtros activos' })).toHaveTextContent('Desde 15-07-2026 10:00');
  });

  it('cambiar un filtro escribe la URL y vuelve a la página 1', async () => {
    const { servidor, router } = montarPanel('/reservas?desde=&page=2');
    await esperarListado();
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Sentido' }), 'URBANO');
    await waitFor(() => expect(router.state.location.search).toBe('?desde=&sentido=URBANO'));
    await userEvent.click(screen.getByText('Todos', { selector: 'summary' }));
    await userEvent.click(screen.getByRole('checkbox', { name: 'Cancelado' }));
    await waitFor(() => expect(router.state.location.search).toBe('?estado=CANCELADO&desde=&sentido=URBANO'));
    await waitFor(() => expect(ultimaConsulta(servidor)).toEqual([['estado', 'CANCELADO'], ['sentido', 'URBANO']]));
  });

  it('la búsqueda se escribe en la URL tras dejar de teclear, reemplazando la entrada del historial', async () => {
    const { router } = montarPanel('/reservas?desde=');
    await esperarListado();
    await userEvent.type(screen.getByRole('searchbox', { name: 'Buscar' }), 'LA123');
    await waitFor(() => expect(router.state.location.search).toBe('?desde=&q=LA123'));
    expect(router.state.historyAction).toBe('REPLACE');
  });

  it('una hora inexistente en `desde` se marca y ese filtro no se aplica', async () => {
    const { servidor } = montarPanel('/reservas?desde=2026-09-06T00%3A30');
    await esperarListado();
    expect(screen.getByText(/Esa hora no existe en Chile .* El filtro no se aplicó\./)).toBeInTheDocument();
    expect(ultimaConsulta(servidor)).toEqual([]);
  });

  it('paginación de 25', async () => {
    const { viajes, router, servidor } = montarPanel('/reservas?desde=');
    viajes.agregar(...Array.from({ length: 30 }, () => viajeDePrueba()));
    await esperarListado();
    expect(screen.getByText(/30 reservas · página 1 de 2/)).toBeInTheDocument();
    expect(screen.getAllByRole('row')).toHaveLength(26); // encabezado + 25
    expect(screen.getByRole('button', { name: 'Anterior' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente' }));
    await waitFor(() => expect(router.state.location.search).toBe('?desde=&page=2'));
    await waitFor(() => expect(screen.getByText(/página 2 de 2/)).toBeInTheDocument());
    expect(screen.getAllByRole('row')).toHaveLength(6);
    expect(ultimaConsulta(servidor)).toEqual([['page', '2']]);
  });

  it('una página que no existe ofrece volver a la primera', async () => {
    const { router } = montarPanel('/reservas?desde=&page=9');
    expect(await screen.findByText('Esa página no existe.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ir a la primera página' }));
    await waitFor(() => expect(router.state.location.search).toBe('?desde='));
  });

  it('vacío sin filtros: «Aún no hay reservas» con «Nueva reserva»', async () => {
    montarPanel('/reservas?desde=');
    expect(await screen.findByText('Aún no hay reservas.')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Nueva reserva' })).toHaveLength(2);
  });

  it('vacío con filtros: «Ninguna reserva coincide» y «Quitar filtros»', async () => {
    const { router } = montarPanel('/reservas?estado=CANCELADO&ordenar=creado_en');
    expect(await screen.findByText('Ninguna reserva coincide con los filtros.')).toBeInTheDocument();
    const quitar = screen.getAllByRole('button', { name: 'Quitar filtros' });
    await userEvent.click(quitar[quitar.length - 1]);
    // Se conserva el orden elegido.
    await waitFor(() => expect(router.state.location.search).toBe('?desde=&ordenar=creado_en'));
  });

  it('cargando: esqueleto mientras llega la respuesta', async () => {
    const { servidor } = montarPanel('/reservas');
    servidor.retener('GET /api/viajes/');
    expect(await screen.findByLabelText('Cargando reservas')).toBeInTheDocument();
    await waitFor(() => expect(servidor.pendientes).toHaveLength(1));
    await act(async () => servidor.entregar());
    await esperarListado();
  });

  it('error: mensaje y Reintentar', async () => {
    const { servidor, viajes } = montarPanel('/reservas?desde=');
    viajes.agregar(viajeDePrueba({ pasajero: { id: 1, nombre: 'Rita Ruiz', telefono: '+56900000002' } }));
    servidor.fallar('GET /api/viajes/', 503);
    expect(await screen.findByText(MENSAJES.sin_conexion)).toBeInTheDocument();
    servidor.reparar();
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('row', { name: /Rita Ruiz/ })).toBeInTheDocument();
  });

  it('un 500 dice que el servidor tuvo un error', async () => {
    const { servidor } = montarPanel('/reservas?desde=');
    servidor.fallar('GET /api/viajes/', 500);
    expect(await screen.findByText(MENSAJES.error_servidor)).toBeInTheDocument();
  });

  it('el desplegable de Estado se cierra al hacer clic fuera o presionar Escape', async () => {
    montarPanel('/reservas?desde=');
    await esperarListado();
    const resumen = screen.getByText('Todos', { selector: 'summary' });
    const detalle = resumen.closest('details')!;

    await userEvent.click(resumen);
    expect(detalle).toHaveAttribute('open');

    await userEvent.pointer({ keys: '[MouseLeft]', target: screen.getByRole('heading', { name: 'Reservas' }) });
    expect(detalle).not.toHaveAttribute('open');

    await userEvent.click(resumen);
    expect(detalle).toHaveAttribute('open');

    await userEvent.keyboard('{Escape}');
    expect(detalle).not.toHaveAttribute('open');
  });

  it('muestra columna N°, conductor/vehículo, convenio y botón Limpiar filtros cuando hay filtros activos', async () => {
    const { viajes, router } = montarPanel('/reservas?estado=ACEPTADO&ordenar=creado_en');
    viajes.agregar(
      viajeDePrueba({
        id: 13,
        estado: 'ACEPTADO',
        pasajero: { id: 1, nombre: 'Laura León', telefono: '+56900000013' },
        conductor: { id: 4, nombre: 'Carlos Chofer' },
        vehiculo: { id: 2, patente: 'ABCD12' },
        convenio: { id: 9, cliente_nombre: 'Hotel Pacífico' },
      }),
    );
    await esperarListado();

    const fila = screen.getByRole('row', { name: /Laura León/ });
    expect(within(fila).getByText('#13')).toBeInTheDocument();
    expect(fila).toHaveTextContent('Carlos Chofer');
    expect(fila).toHaveTextContent('ABCD12');
    expect(fila).toHaveTextContent('Hotel Pacífico');
    expect(within(fila).getByRole('link', { name: 'Ver detalle' })).toHaveAttribute('href', '/reservas/13');

    await userEvent.click(screen.getByRole('button', { name: 'Limpiar filtros' }));
    await waitFor(() => expect(router.state.location.search).toBe('?desde=&ordenar=creado_en'));
  });

  it('acción rápida Asignar en reservas Solicitado abre el diálogo y asigna al conductor', async () => {
    const { viajes } = montarPanel('/reservas?desde=');
    viajes.agregar(viajeDePrueba({ id: 21, estado: 'SOLICITADO', pasajero: { id: 2, nombre: 'Mario Soto', telefono: '+56900000021' } }));
    viajes.candidatos = [
      {
        id: 5,
        nombre: 'Macarena Gutiérrez',
        patente: 'DMAA10',
        distancia_m: 450,
        posicion_en: null,
        confiable: true,
        posicion_fila: null,
        ultimo_viaje_en: null,
        sugerido: true,
      },
    ];
    await esperarListado();

    const fila = screen.getByRole('row', { name: /Mario Soto/ });
    await userEvent.click(within(fila).getByRole('button', { name: 'Asignar' }));
    expect(await screen.findByRole('heading', { name: 'Asignar la reserva #21' })).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Asignar a Macarena Gutiérrez' }));
    expect(await screen.findByText(/Reserva #21 asignada a Macarena Gutiérrez/)).toBeInTheDocument();
  });
});
