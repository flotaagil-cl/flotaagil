/** HU-69: pantalla «Vuelos de hoy» del panel (administrador y despachador). */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { components } from '../api/esquema';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { viajeDePrueba, type ServidorViajesFalso } from '../pruebas/servidorViajesFalso';
import { REFRESCO_MS } from './VuelosDeHoy';

type Viaje = components['schemas']['Viaje'];

const RUTA = '/api/vuelos-de-hoy/';
const RUTA_CONSULTAR = '/api/vuelos-de-hoy/consultar/';
const en = (min: number) => new Date(Date.now() + min * 60_000).toISOString();

function llegada(id: number, cambios: Partial<components['schemas']['Vuelo']> = {}, viaje: Partial<Viaje> = {}) {
  return viajeDePrueba({
    id,
    sentido: 'DESDE_AEROPUERTO',
    recogida_en: en(80),
    pasajero: { id, nombre: `Pasajera ${id}`, telefono: '+56900000001' },
    vuelo: {
      numero: `LA${id}`,
      fecha: '2026-11-18',
      hora_programada: en(60),
      hora_estimada: null,
      estado_vuelo: 'PROGRAMADO',
      ultima_consulta_en: en(-5),
      origen_icao: null,
      recogida_propuesta: null,
      propuesta_en: null,
      internacional: null,
      margen_min: 20,
      recogida_sugerida: en(80),
      ...cambios,
    },
    ...viaje,
  });
}

class ServidorVuelosFalso {
  consultas: URLSearchParams[] = [];
  peticionesConsultar: { rango?: string }[] = [];
  private readonly anterior: ServidorAuthFalso['api'];

  constructor(
    auth: ServidorAuthFalso,
    private readonly viajes: ServidorViajesFalso,
  ) {
    this.anterior = auth.api;
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    if (url.pathname === RUTA_CONSULTAR && peticion.method === 'POST') {
      const cuerpo = (await peticion.json()) as { rango?: string };
      this.peticionesConsultar.push(cuerpo);
      return {
        estado: 200,
        cuerpo: { consultados: 2, actualizados: 2, sin_datos: 0 },
      };
    }
    if (url.pathname !== RUTA) return this.anterior!(peticion, url);
    this.consultas.push(url.searchParams);
    const tipo = url.searchParams.get('tipo');
    const estado = url.searchParams.get('estado');
    const todos = this.viajes.viajes;
    const filtrados = todos.filter(
      (v) =>
        (tipo !== 'llegadas' || v.vuelo) && (tipo !== 'salidas' || !v.vuelo) && (!estado || v.vuelo?.estado_vuelo === estado),
    );
    return {
      estado: 200,
      cuerpo: {
        fecha: url.searchParams.get('rango') === 'manana' ? '2026-11-19' : '2026-11-18',
        contadores: {
          demorados: todos.filter((v) => v.vuelo?.estado_vuelo === 'DEMORADO').length,
          cancelados_o_desviados: todos.filter((v) => v.vuelo?.estado_vuelo === 'CANCELADO').length,
          sin_conductor: todos.filter((v) => !v.conductor).length,
          propuestas_pendientes: todos.filter((v) => v.vuelo?.recogida_propuesta).length,
        },
        viajes: filtrados,
      },
    };
  }
}

function montar(email = 'despacho@andes.example', ruta = '/vuelos-de-hoy') {
  const contexto = montarPanel(ruta, { email });
  contexto.viajes.agregar(
    viajeDePrueba({
      id: 30,
      sentido: 'HACIA_AEROPUERTO',
      recogida_en: en(30),
      vuelo_salida_en: en(240),
      vuelo_salida_tipo: 'INTERNACIONAL',
      en_aeropuerto_a_las: en(60),
      pasajero: { id: 30, nombre: 'Pasajera de salida', telefono: '+56900000002' },
      conductor: { id: 3, nombre: 'Carla Conductora' },
    }),
    llegada(31, { estado_vuelo: 'DEMORADO', hora_estimada: en(100), recogida_propuesta: en(120) }),
    llegada(32, { estado_vuelo: 'CANCELADO' }),
  );
  return { ...contexto, vuelos: new ServidorVuelosFalso(contexto.servidor, contexto.viajes) };
}

afterEach(() => {
  vi.useRealTimers();
});

describe('permisos', () => {
  it.each(['admin@andes.example', 'despacho@andes.example'])('%s la ve en el menú', async (email) => {
    montar(email, '/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Vuelos de hoy' })).toHaveAttribute('href', '/vuelos-de-hoy');
  });
});

describe('tabla', () => {
  it('contadores, estados con texto, salida con su hora en el aeropuerto y conductor sin asignar', async () => {
    montar();
    const resumen = await screen.findByRole('list', { name: 'Resumen del día' });
    expect(resumen).toHaveTextContent('1 demorados');
    expect(resumen).toHaveTextContent('1 cancelados o desviados');
    expect(resumen).toHaveTextContent('2 sin conductor');
    expect(resumen).toHaveTextContent('1 propuestas de recogida pendientes');
    const filas = within(screen.getByRole('table', { name: 'Vuelos de hoy' })).getAllByRole('row').slice(1);
    expect(filas).toHaveLength(3);
    expect(filas[0]).toHaveTextContent('Salida (internacional)');
    expect(filas[0]).toHaveTextContent('No se monitorea');
    expect(filas[0]).toHaveTextContent(/Debe estar en el aeropuerto a las \d\d:\d\d/);
    expect(filas[0]).toHaveTextContent('despega en 4 h');
    expect(filas[1]).toHaveTextContent(/demorado 40 min/);
    expect(filas[1]).toHaveTextContent('aterriza en 1 h 40 min');
    expect(filas[1]).toHaveTextContent('Sin asignar');
    expect(filas[2]).toHaveTextContent('CANCELADO por la aerolínea · revisar con el pasajero');
    expect(within(filas[1]).getByRole('link', { name: 'LA31' })).toHaveAttribute('href', '/reservas/31');
  });

  it('filtra por llegadas y por estado, y el estado no aplica a las salidas', async () => {
    const { vuelos } = montar();
    await screen.findByRole('table', { name: 'Vuelos de hoy' });
    await userEvent.click(screen.getByRole('radio', { name: 'Llegadas' }));
    await waitFor(() => expect(vuelos.consultas.at(-1)?.get('tipo')).toBe('llegadas'));
    await userEvent.selectOptions(screen.getByLabelText('Estado del vuelo'), 'DEMORADO');
    await waitFor(() => expect(screen.getAllByRole('row')).toHaveLength(2));
    expect(vuelos.consultas.at(-1)?.get('estado')).toBe('DEMORADO');
    await userEvent.click(screen.getByRole('radio', { name: 'Salidas' }));
    expect(screen.getByLabelText('Estado del vuelo')).toBeDisabled();
  });

  it('permite cambiar el rango de días y consultar estados ahora', async () => {
    const { vuelos } = montar();
    await screen.findByRole('table', { name: 'Vuelos de hoy' });

    expect(screen.getByRole('radio', { name: 'Hoy' })).toBeChecked();
    await userEvent.click(screen.getByRole('radio', { name: 'Mañana' }));
    await waitFor(() => expect(vuelos.consultas.at(-1)?.get('rango')).toBe('manana'));
    expect(await screen.findByText(/19-11-2026/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole('radio', { name: 'Próximos 3 días' }));
    await waitFor(() => expect(vuelos.consultas.at(-1)?.get('rango')).toBe('proximos_3_dias'));

    await userEvent.click(screen.getByRole('button', { name: 'Consultar ahora' }));
    await waitFor(() => expect(vuelos.peticionesConsultar).toEqual([{ rango: 'proximos_3_dias' }]));
    expect(await screen.findByRole('status')).toHaveTextContent('Estados actualizados: 2 de 2 vuelos consultados.');
  });

  it('sin vuelos lo dice', async () => {
    const { viajes } = montar();
    viajes.viajes = [];
    expect(await screen.findByText('No hay vuelos con estos filtros hoy.')).toBeInTheDocument();
  });

  it('confirma la propuesta de recogida desde la fila (RN-02)', async () => {
    const { viajes } = montar();
    const boton = await screen.findByRole('button', { name: /Confirmar la recogida a las \d\d:\d\d de la reserva 31/ });
    await userEvent.click(boton);
    await waitFor(() => expect(screen.queryByRole('button', { name: /de la reserva 31/ })).not.toBeInTheDocument());
    expect(viajes.cuerpos.at(-1)?.ruta).toBe('POST /api/viajes/31/confirmar-recogida/');
    expect(screen.getByRole('list', { name: 'Resumen del día' })).toHaveTextContent('0 propuestas de recogida pendientes');
  });

  it('se actualiza sola cada minuto', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const { vuelos } = montar();
    await screen.findByRole('table', { name: 'Vuelos de hoy' });
    const antes = vuelos.consultas.length;
    await act(() => vi.advanceTimersByTimeAsync(REFRESCO_MS));
    await waitFor(() => expect(vuelos.consultas.length).toBeGreaterThan(antes));
  });
});
