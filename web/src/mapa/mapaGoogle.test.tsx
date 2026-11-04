/** Adaptador de Google Maps (PR-12): con un doble de la API, porque no hay clave real con la que probarlo. */

import { act, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { ConductorMapa } from './estado';
import { cargarGoogleMaps, datosMarcador, olvidarCargaDeGoogleMaps } from './googleMaps';
import { MapaGoogle } from './MapaGoogle';

const AHORA = Date.parse('2026-11-03T15:00:00Z');
const CLAVE = 'clave-sintetica';

const conductor = (id: number, cambios: Partial<ConductorMapa> = {}): ConductorMapa => ({
  id,
  nombre: `Conductor ${id}`,
  estado: 'DISPONIBLE',
  patente: `ABCD${id}${id}`,
  posicion: { lat: -33.4, lon: -70.6, precision_m: 8, registrada_en: new Date(AHORA - 5000).toISOString() },
  ...cambios,
});

class MarcadorFalso {
  static creados: MarcadorFalso[] = [];
  mapa: unknown;
  posicion: unknown;
  titulo = '';
  etiqueta: { text?: string } = {};
  icono: { fillColor?: string; scale?: number } = {};
  indice = 0;
  clic: (() => void) | null = null;
  constructor(opciones: { map: unknown }) {
    this.mapa = opciones.map;
    MarcadorFalso.creados.push(this);
  }
  setPosition(p: unknown) {
    this.posicion = p;
  }
  setTitle(t: string) {
    this.titulo = t;
  }
  setLabel(e: { text?: string }) {
    this.etiqueta = e;
  }
  setIcon(i: { fillColor?: string; scale?: number }) {
    this.icono = i;
  }
  setZIndex(i: number) {
    this.indice = i;
  }
  setMap(m: unknown) {
    this.mapa = m;
  }
  addListener(_: string, accion: () => void) {
    this.clic = accion;
  }
}

class MapaFalso {
  static creados: MapaFalso[] = [];
  encuadres = 0;
  centrados: unknown[] = [];
  constructor(
    readonly elemento: HTMLElement,
    readonly opciones: object,
  ) {
    MapaFalso.creados.push(this);
  }
  fitBounds() {
    this.encuadres += 1;
  }
  panTo(p: unknown) {
    this.centrados.push(p);
  }
}

class LimitesFalsos {
  extend() {}
}

function scripts() {
  return [...document.head.querySelectorAll<HTMLScriptElement>('script[src*="maps.googleapis.com"]')];
}

/** Lo que hace Google al terminar de cargar su script. */
async function googleTermina() {
  const ventana = window as unknown as Record<string, unknown>;
  ventana.google = { maps: { Map: MapaFalso, Marker: MarcadorFalso, LatLngBounds: LimitesFalsos, SymbolPath: { CIRCLE: 0 } } };
  await act(async () => {
    (ventana.__flotaagilMapaListo as () => void)();
    await Promise.resolve();
  });
}

function montar(conductores: ConductorMapa[], extra: Partial<Parameters<typeof MapaGoogle>[0]> = {}) {
  const alSeleccionar = vi.fn();
  const alFallar = vi.fn();
  const props = { clave: CLAVE, conductores, seleccionado: null, alSeleccionar, ahora: AHORA, alFallar, ...extra };
  const vista = render(<MapaGoogle {...props} />);
  return { ...vista, alSeleccionar, alFallar, props };
}

beforeEach(() => {
  MarcadorFalso.creados = [];
  MapaFalso.creados = [];
  olvidarCargaDeGoogleMaps();
});

afterEach(() => {
  scripts().forEach((s) => s.remove());
  const ventana = window as unknown as Record<string, unknown>;
  delete ventana.google;
  delete ventana.gm_authFailure;
  delete ventana.__flotaagilMapaListo;
});

describe('datos del marcador', () => {
  it('color por estado; gris y translúcido si no es confiable', () => {
    expect(datosMarcador(conductor(1), null, AHORA)?.color).toBe('#15803d');
    expect(datosMarcador(conductor(1, { estado: 'EN_VIAJE' }), null, AHORA)?.color).toBe('#b45309');
    const antigua = datosMarcador(conductor(1), null, AHORA + 120_000);
    expect(antigua?.color).toBe('#9ca3af');
    expect(antigua?.opacidad).toBeLessThan(1);
  });

  it('sin posición no hay marcador; sin patente usa el nombre', () => {
    expect(datosMarcador(conductor(1, { posicion: null }), null, AHORA)).toBeNull();
    expect(datosMarcador(conductor(1, { patente: null }), null, AHORA)?.etiqueta).toBe('Conductor');
  });

  it('el seleccionado se ve más grande', () => {
    expect(datosMarcador(conductor(1), 1, AHORA)?.escala).toBeGreaterThan(datosMarcador(conductor(1), null, AHORA)?.escala ?? 0);
  });
});

describe('carga del script', () => {
  it('pide el script una sola vez, con la clave y en español', async () => {
    void cargarGoogleMaps(CLAVE);
    void cargarGoogleMaps(CLAVE);
    expect(scripts()).toHaveLength(1);
    const url = new URL(scripts()[0].src);
    expect(url.searchParams.get('key')).toBe(CLAVE);
    expect(url.searchParams.get('language')).toBe('es');
    expect(url.searchParams.get('region')).toBe('CL');
    await googleTermina();
  });

  it('si falla la red se puede volver a intentar', async () => {
    const primera = cargarGoogleMaps(CLAVE);
    scripts()[0].dispatchEvent(new Event('error'));
    await expect(primera).rejects.toThrow('No se pudo cargar');
    expect(scripts()).toHaveLength(0);
    void cargarGoogleMaps(CLAVE);
    expect(scripts()).toHaveLength(1);
    await googleTermina();
  });

  it('avisa si el script termina sin dejar la API disponible', async () => {
    const carga = cargarGoogleMaps(CLAVE);
    (window as unknown as Record<string, () => void>).__flotaagilMapaListo();
    await expect(carga).rejects.toThrow('no quedó disponible');
  });
});

describe('mapa', () => {
  it('dibuja un marcador por conductor con posición y encuadra una vez', async () => {
    const { props, rerender } = montar([conductor(1), conductor(2), conductor(3, { posicion: null })]);
    await googleTermina();
    expect(MarcadorFalso.creados).toHaveLength(2);
    expect(MarcadorFalso.creados[0].etiqueta.text).toBe('ABCD11');
    expect(MarcadorFalso.creados[0].titulo).toBe('Conductor 1');
    expect(MapaFalso.creados[0].encuadres).toBe(1);
    rerender(<MapaGoogle {...props} conductores={[conductor(1, { posicion: { lat: -33.5, lon: -70.7, precision_m: 8, registrada_en: new Date(AHORA).toISOString() } }), conductor(2)]} />);
    expect(MapaFalso.creados[0].encuadres).toBe(1);
  });

  it('una posición nueva mueve el marcador existente, sin crear otro', async () => {
    const { props, rerender } = montar([conductor(1)]);
    await googleTermina();
    rerender(<MapaGoogle {...props} conductores={[conductor(1, { posicion: { lat: -33.5, lon: -70.7, precision_m: 8, registrada_en: new Date(AHORA).toISOString() } })]} />);
    expect(MarcadorFalso.creados).toHaveLength(1);
    expect(MarcadorFalso.creados[0].posicion).toEqual({ lat: -33.5, lng: -70.7 });
  });

  it('el conductor que sale de turno pierde su marcador', async () => {
    const { props, rerender } = montar([conductor(1), conductor(2)]);
    await googleTermina();
    rerender(<MapaGoogle {...props} conductores={[conductor(1)]} />);
    expect(MarcadorFalso.creados[1].mapa).toBeNull();
    expect(MarcadorFalso.creados[0].mapa).not.toBeNull();
  });

  it('el clic selecciona y la selección lleva al conductor', async () => {
    const { props, rerender, alSeleccionar } = montar([conductor(1)]);
    await googleTermina();
    MarcadorFalso.creados[0].clic?.();
    expect(alSeleccionar).toHaveBeenCalledWith(1);
    rerender(<MapaGoogle {...props} seleccionado={1} />);
    expect(MapaFalso.creados[0].centrados).toEqual([{ lat: -33.4, lng: -70.6 }]);
    expect(MarcadorFalso.creados[0].indice).toBe(2);
  });

  it('una posición nueva del elegido no vuelve a mover el mapa', async () => {
    const { props, rerender } = montar([conductor(1)], { seleccionado: 1 });
    await googleTermina();
    expect(MapaFalso.creados[0].centrados).toHaveLength(1);
    rerender(<MapaGoogle {...props} conductores={[conductor(1, { posicion: { lat: -33.5, lon: -70.7, precision_m: 8, registrada_en: new Date(AHORA).toISOString() } })]} />);
    expect(MapaFalso.creados[0].centrados).toHaveLength(1);
  });

  it('al salir de la pantalla quita los marcadores', async () => {
    const { unmount } = montar([conductor(1)]);
    await googleTermina();
    unmount();
    expect(MarcadorFalso.creados[0].mapa).toBeNull();
  });

  it('la región queda rotulada para lectores de pantalla', () => {
    montar([]);
    expect(screen.getByRole('region', { name: 'Mapa de conductores en turno' })).toBeInTheDocument();
  });

  it('avisa si la red falla', async () => {
    const { alFallar } = montar([conductor(1)]);
    await act(async () => {
      scripts()[0].dispatchEvent(new Event('error'));
      await Promise.resolve();
    });
    expect(alFallar).toHaveBeenCalledTimes(1);
  });

  it('avisa si Google rechaza la clave después de cargar', async () => {
    const { alFallar } = montar([conductor(1)]);
    await googleTermina();
    act(() => (window as unknown as Record<string, () => void>).gm_authFailure());
    expect(alFallar).toHaveBeenCalledTimes(1);
  });
});
