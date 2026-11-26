/** HU-71: el mapa de las direcciones: qué pines se ponen y cómo se centra (Leaflet simulado, sin red). */

import { render, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { MapaOsmPortal } from '../../mapa/MapaOsmPortal';
import { mapaDeDirecciones, SCL } from './direcciones';
import { ProveedorMapa } from './Mapa';
import { MapaDirecciones } from './MapaDirecciones';

const leaflet = vi.hoisted(() => {
  const llamadas = { centrados: [] as [unknown, number][], encuadres: [] as [unknown, unknown][], lineas: [] as [unknown, Record<string, unknown>][], pines: [] as string[] };
  const capa = { addTo: () => capa, remove: () => undefined };
  const L = {
    map: () => {
      const mapa = {
        setView: (centro: unknown, zoom: number) => (llamadas.centrados.push([centro, zoom]), mapa),
        fitBounds: (puntos: unknown, opciones: unknown) => llamadas.encuadres.push([puntos, opciones]),
        remove: () => undefined,
      };
      return mapa;
    },
    layerGroup: () => capa,
    polyline: (puntos: unknown, estilo: Record<string, unknown>) => (llamadas.lineas.push([puntos, estilo]), capa),
    divIcon: (opciones: unknown) => opciones,
    marker: (_punto: unknown, opciones: { title: string }) => (llamadas.pines.push(opciones.title), capa),
  };
  return { llamadas, L };
});
vi.mock('../../mapa/osm', () => ({ cargarLeaflet: async () => leaflet.L, capaOsm: () => ({ addTo: () => undefined }) }));

const CASA = { lat: -33.4255, lon: -70.6105 };
const OFICINA = { lat: -33.4168, lon: -70.5956 };

afterEach(() => Object.values(leaflet.llamadas).forEach((lista) => lista.splice(0)));

describe('pines según el tipo de viaje', () => {
  const nombres = (...args: Parameters<typeof mapaDeDirecciones>) => mapaDeDirecciones(...args).marcadores.map((m) => m.etiqueta);

  it('en la ciudad: solo lo elegido; con los dos, además la línea', () => {
    expect(nombres('en-la-ciudad')).toEqual([]);
    expect(nombres('en-la-ciudad', CASA)).toEqual(['Punto de recogida']);
    expect(mapaDeDirecciones('en-la-ciudad', CASA).ruta).toBeUndefined();
    expect(mapaDeDirecciones('en-la-ciudad', CASA, OFICINA).ruta).toEqual({ desde: { lat: CASA.lat, lng: CASA.lon }, hasta: { lat: OFICINA.lat, lng: OFICINA.lon } });
  });

  it('de aeropuerto: SCL en su extremo, salvo que traiga un punto guardado', () => {
    expect(nombres('desde-aeropuerto')).toEqual(['Aeropuerto de Santiago (SCL)']);
    expect(nombres('desde-aeropuerto', null, OFICINA)).toEqual(['Aeropuerto de Santiago (SCL)', 'Destino']);
    expect(nombres('al-aeropuerto', CASA)).toEqual(['Punto de recogida', 'Aeropuerto de Santiago (SCL)']);
    expect(mapaDeDirecciones('al-aeropuerto', CASA).ruta?.hasta).toEqual(SCL);
    expect(mapaDeDirecciones('desde-aeropuerto', { lat: -33.4, lon: -70.8 }).marcadores[0].punto).toEqual({ lat: -33.4, lng: -70.8 });
  });

  it('sin tipo elegido, solo el aeropuerto', () => {
    expect(nombres(null, CASA, OFICINA)).toEqual(['Aeropuerto de Santiago (SCL)']);
  });
});

describe('centrado en OpenStreetMap', () => {
  const montar = (props: Parameters<typeof MapaDirecciones>[0]) => {
    const vista = (p: typeof props) => (
      <ProveedorMapa componente={MapaOsmPortal}>
        <MapaDirecciones {...p} />
      </ProveedorMapa>
    );
    const { rerender } = render(vista(props));
    return (nuevas: typeof props) => rerender(vista(nuevas));
  };

  it('con un punto centra con zoom 15; con los dos encuadra y los une con línea punteada', async () => {
    const cambiar = montar({ tipo: 'en-la-ciudad', origen: CASA, chico: true });
    await waitFor(() => expect(leaflet.llamadas.centrados.at(-1)).toEqual([[CASA.lat, CASA.lon], 15]));
    expect(leaflet.llamadas.encuadres).toEqual([]);

    cambiar({ tipo: 'en-la-ciudad', origen: CASA, destino: OFICINA, chico: true });
    await waitFor(() => expect(leaflet.llamadas.encuadres).toHaveLength(1));
    expect(leaflet.llamadas.encuadres[0][1]).toEqual({ padding: [40, 40], maxZoom: 15 });
    expect(leaflet.llamadas.lineas.at(-1)![1]).toMatchObject({ dashArray: '8 8' });
    expect(leaflet.llamadas.pines.slice(-2)).toEqual(['Punto de recogida', 'Destino']);

    // Los mismos puntos en objetos nuevos (otra tecla en el formulario) no vuelven a encuadrar.
    cambiar({ tipo: 'en-la-ciudad', origen: { ...CASA }, destino: { ...OFICINA }, chico: true });
    expect(leaflet.llamadas.encuadres).toHaveLength(1);
  });

  it('en un viaje de aeropuerto sin dirección elegida centra en SCL', async () => {
    montar({ tipo: 'desde-aeropuerto' });
    await waitFor(() => expect(leaflet.llamadas.centrados.at(-1)).toEqual([[SCL.lat, SCL.lng], 15]));
  });
});
