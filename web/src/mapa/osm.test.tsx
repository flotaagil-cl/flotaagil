/** HU-70 (DC-71): OpenStreetMap con Leaflet simulado (sin red), elección del proveedor y caída al esquemático. */

import { act, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ConductorMapa } from './estado';
import { MapaOsm } from './MapaOsm';
import { MapaOsmPortal } from './MapaOsmPortal';
import { ATRIBUCION_OSM, olvidarCargaDeLeaflet, TESELAS_OSM } from './osm';
import { elegirProveedor } from '../diseno/mapa/proveedor';

type Oyente = () => void;

const leaflet = vi.hoisted(() => {
  const estado = {
    mapas: [] as { setView: unknown; encuadres: unknown[]; centrados: unknown[]; quitado: boolean }[],
    capas: [] as { url: string; opciones: Record<string, unknown>; oyentes: Record<string, (() => void)[]> }[],
    marcadores: [] as Record<string, unknown>[],
    pines: [] as { punto: unknown; opciones: { title: string; icon: { html: string } } }[],
    lineas: [] as unknown[],
  };
  const encadenable = <T extends object>(objeto: T) => Object.assign(objeto, { addTo: () => objeto, remove: () => undefined });
  const L = {
    map: () => {
      const mapa = { setView: null as unknown, encuadres: [] as unknown[], centrados: [] as unknown[], quitado: false };
      const api = {
        setView: (centro: unknown) => ((mapa.setView = centro), api),
        fitBounds: (limites: unknown) => mapa.encuadres.push(limites),
        panTo: (punto: unknown) => mapa.centrados.push(punto),
        remove: () => (mapa.quitado = true),
      };
      estado.mapas.push(mapa);
      return api;
    },
    tileLayer: (url: string, opciones: Record<string, unknown>) => {
      const capa = { url, opciones, oyentes: {} as Record<string, (() => void)[]> };
      estado.capas.push(capa);
      return encadenable({ on: (evento: string, fn: () => void) => (capa.oyentes[evento] ??= []).push(fn) });
    },
    circleMarker: (punto: unknown, opciones: Record<string, unknown>) => {
      const marcador: Record<string, unknown> = { punto, opciones, quitado: false, alFrente: 0 };
      estado.marcadores.push(marcador);
      return Object.assign(marcador, {
        bindTooltip: (texto: string) => (marcador.etiqueta = texto),
        on: (_: string, fn: () => void) => (marcador.clic = fn),
        addTo: () => marcador,
        setLatLng: (p: unknown) => (marcador.punto = p),
        setStyle: (o: Record<string, unknown>) => (marcador.opciones = o),
        setRadius: (r: number) => (marcador.radio = r),
        setTooltipContent: (t: string) => (marcador.etiqueta = t),
        bringToFront: () => (marcador.alFrente = (marcador.alFrente as number) + 1),
        remove: () => (marcador.quitado = true),
      });
    },
    layerGroup: () => encadenable({}),
    polyline: (puntos: unknown) => (estado.lineas.push(puntos), encadenable({})),
    divIcon: (opciones: object) => opciones,
    marker: (punto: unknown, opciones: { title: string; icon: { html: string } }) => (estado.pines.push({ punto, opciones }), encadenable({})),
  };
  return { estado, L };
});

vi.mock('leaflet', () => ({ default: leaflet.L }));
vi.mock('leaflet/dist/leaflet.css', () => ({}));

const AHORA = Date.parse('2026-11-03T15:00:00Z');
const conductor = (id: number, cambios: Partial<ConductorMapa> = {}): ConductorMapa => ({
  id,
  nombre: `Conductor ${id}`,
  estado: 'DISPONIBLE',
  patente: `ABCD${id}${id}`,
  posicion: { lat: -33.4, lon: -70.6, precision_m: 8, registrada_en: new Date(AHORA - 5000).toISOString() },
  ...cambios,
});

function emitir(evento: string, veces = 1) {
  act(() => {
    for (let i = 0; i < veces; i += 1) leaflet.estado.capas.at(-1)!.oyentes[evento]?.forEach((fn: Oyente) => fn());
  });
}

beforeEach(() => {
  Object.assign(leaflet.estado, { mapas: [], capas: [], marcadores: [], pines: [], lineas: [] });
  olvidarCargaDeLeaflet();
});

afterEach(() => {
  vi.unstubAllEnvs();
});

describe('elección del proveedor', () => {
  it.each([
    [{ VITE_MAPA_PROVEEDOR: 'osm', VITE_GOOGLE_MAPS_KEY: 'clave' }, 'osm'],
    [{ VITE_MAPA_PROVEEDOR: 'ESQUEMATICO', DEV: true }, 'esquematico'],
    [{ VITE_MAPA_PROVEEDOR: 'google', VITE_GOOGLE_MAPS_KEY: 'clave' }, 'google'],
    [{ VITE_MAPA_PROVEEDOR: 'google' }, 'esquematico'], // sin clave, Google no puede
    [{ VITE_GOOGLE_MAPS_KEY: 'clave', DEV: true }, 'google'],
    [{ DEV: true }, 'osm'], // desarrollo sin clave: OSM
    [{ DEV: false }, 'esquematico'], // producción sin clave: el esquemático, como hoy
    [{ VITE_MAPA_PROVEEDOR: 'otro', DEV: true }, 'osm'],
  ] as const)('%o → %s', (entorno, esperado) => {
    expect(elegirProveedor(entorno)).toBe(esperado);
  });
});

describe('mapa en vivo del panel con OpenStreetMap', () => {
  const props = { seleccionado: null, alSeleccionar: vi.fn(), ahora: AHORA, alFallar: vi.fn() };

  it('teselas de tile.openstreetmap.org con la atribución, marcadores por estado y selección', async () => {
    const alSeleccionar = vi.fn();
    const { rerender } = render(<MapaOsm {...props} alSeleccionar={alSeleccionar} conductores={[conductor(1), conductor(2, { estado: 'EN_VIAJE' })]} />);
    await waitFor(() => expect(leaflet.estado.marcadores).toHaveLength(2));
    expect(screen.getByRole('region', { name: 'Mapa de conductores en turno' })).toBeInTheDocument();
    const capa = leaflet.estado.capas[0];
    expect(capa.url).toBe(TESELAS_OSM);
    expect(capa.opciones).toMatchObject({ attribution: ATRIBUCION_OSM, maxZoom: 19 });
    expect(ATRIBUCION_OSM).toContain('OpenStreetMap</a> contributors');
    const [disponible, enViaje] = leaflet.estado.marcadores;
    expect(disponible.etiqueta).toBe('ABCD11');
    expect((disponible.opciones as { fillColor: string }).fillColor).toBe('#15803d');
    expect((enViaje.opciones as { fillColor: string }).fillColor).toBe('#b45309');
    expect(leaflet.estado.mapas[0].encuadres).toHaveLength(1);
    act(() => (disponible.clic as Oyente)());
    expect(alSeleccionar).toHaveBeenCalledWith(1);
    // Seleccionado: más grande, al frente y centrado; un conductor que sale de turno se quita.
    rerender(<MapaOsm {...props} alSeleccionar={alSeleccionar} seleccionado={1} conductores={[conductor(1)]} />);
    expect(disponible.radio).toBe(13);
    expect(disponible.alFrente).toBeGreaterThan(0);
    expect(enViaje.quitado).toBe(true);
    expect(leaflet.estado.mapas[0].centrados).toEqual([[-33.4, -70.6]]);
    expect(leaflet.estado.mapas[0].encuadres).toHaveLength(1);

    // Reencuadrar flota ejecuta fitBounds nuevamente.
    rerender(<MapaOsm {...props} alSeleccionar={alSeleccionar} seleccionado={1} reencuadrar={1} conductores={[conductor(1)]} />);
    expect(leaflet.estado.mapas[0].encuadres).toHaveLength(2);
  });

  it('una posición antigua se ve gris y semitransparente', async () => {
    const antigua = conductor(3, { posicion: { lat: -33.4, lon: -70.6, precision_m: 8, registrada_en: new Date(AHORA - 120_000).toISOString() } });
    render(<MapaOsm {...props} conductores={[antigua]} />);
    await waitFor(() => expect(leaflet.estado.marcadores).toHaveLength(1));
    expect(leaflet.estado.marcadores[0].opciones).toMatchObject({ fillColor: '#9ca3af', fillOpacity: 0.55 });
  });

  it('si no carga ninguna tesela (sin internet) avisa para volver al esquemático', async () => {
    const alFallar = vi.fn();
    render(<MapaOsm {...props} alFallar={alFallar} conductores={[]} />);
    await waitFor(() => expect(leaflet.estado.capas).toHaveLength(1));
    emitir('tileerror', 2);
    expect(alFallar).not.toHaveBeenCalled();
    emitir('tileerror');
    expect(alFallar).toHaveBeenCalledTimes(1);
  });

  it('con alguna tesela cargada, un error suelto no lo derriba', async () => {
    const alFallar = vi.fn();
    render(<MapaOsm {...props} alFallar={alFallar} conductores={[]} />);
    await waitFor(() => expect(leaflet.estado.capas).toHaveLength(1));
    emitir('tileload');
    emitir('tileerror', 5);
    expect(alFallar).not.toHaveBeenCalled();
  });

  it('si Leaflet no carga, avisa', async () => {
    vi.resetModules();
    vi.doMock('leaflet', () => {
      throw new Error('sin red');
    });
    const { MapaOsm: Fresco } = await import('./MapaOsm');
    const alFallar = vi.fn();
    render(<Fresco {...props} alFallar={alFallar} conductores={[]} />);
    await waitFor(() => expect(alFallar).toHaveBeenCalled());
    vi.doMock('leaflet', () => ({ default: leaflet.L }));
  });
});

describe('mapas del portal con OpenStreetMap', () => {
  const props = {
    etiqueta: 'Mapa: tu recogida y el aeropuerto',
    marcadores: [
      { id: 'o', punto: { lat: -33.42, lng: -70.6 }, tipo: 'origen' as const, etiqueta: 'Tu recogida' },
      { id: 'a', punto: { lat: -33.39, lng: -70.79 }, tipo: 'aeropuerto' as const, etiqueta: 'Aeropuerto SCL' },
    ],
    ruta: { desde: { lat: -33.42, lng: -70.6 }, hasta: { lat: -33.39, lng: -70.79 } },
  };

  it('pines con su etiqueta, ruta y encuadre', async () => {
    render(<MapaOsmPortal {...props} />);
    await waitFor(() => expect(leaflet.estado.pines).toHaveLength(2));
    expect(screen.getByRole('region', { name: props.etiqueta })).toBeInTheDocument();
    expect(leaflet.estado.pines.map((p) => p.opciones.title)).toEqual(['Tu recogida', 'Aeropuerto SCL']);
    expect(leaflet.estado.pines[1].opciones.icon.html).toContain('data-tipo="aeropuerto"');
    expect(leaflet.estado.lineas).toHaveLength(1);
    expect(leaflet.estado.mapas[0].encuadres).toHaveLength(1);
  });

  it('si las teselas no cargan, vuelve al mapa de respaldo', async () => {
    render(<MapaOsmPortal {...props} />);
    await waitFor(() => expect(leaflet.estado.capas).toHaveLength(1));
    emitir('tileerror', 3);
    expect(await screen.findByRole('img', { name: props.etiqueta })).toBeInTheDocument();
    expect(screen.queryByRole('region', { name: props.etiqueta })).not.toBeInTheDocument();
  });
});

describe('página del mapa con VITE_MAPA_PROVEEDOR=osm', () => {
  class SocketMudo {
    onopen = null;
    onmessage = null;
    onclose = null;
    close() {}
  }

  it('dibuja OpenStreetMap y, si las teselas no cargan, vuelve al esquemático y lo avisa', async () => {
    vi.stubEnv('VITE_MAPA_PROVEEDOR', 'osm');
    vi.stubGlobal('WebSocket', SocketMudo);
    const { montarPanel } = await import('../pruebas/montar');
    montarPanel('/mapa', { email: 'despacho@andes.example' });
    expect(await screen.findByRole('region', { name: 'Mapa de conductores en turno' })).toBeInTheDocument();
    await waitFor(() => expect(leaflet.estado.capas).toHaveLength(1));
    emitir('tileerror', 3);
    expect(await screen.findByText('No se pudo cargar OpenStreetMap: se muestra el mapa esquemático.')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Mapa de conductores en turno' })).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});
