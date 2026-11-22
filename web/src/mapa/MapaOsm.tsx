import type * as Leaflet from 'leaflet';
import { useEffect, useRef, useState } from 'react';
import { encuadre, type ConductorMapa } from './estado';
import { datosMarcador, type DatosMarcador } from './googleMaps';
import estilos from './mapa.module.css';
import { capaOsm, cargarLeaflet, type L } from './osm';

interface Props {
  conductores: ConductorMapa[];
  seleccionado: number | null;
  alSeleccionar: (id: number) => void;
  ahora: number;
  /** No cargó Leaflet o ninguna tesela: quien lo usa vuelve al mapa esquemático. */
  alFallar: () => void;
  /** Contador incremental para reencuadrar toda la flota con posición válida (`fitBounds`). */
  reencuadrar?: number;
  /** Contador incremental para centrar de nuevo en el conductor seleccionado. */
  enfoque?: number;
}

/**
 * HU-70 (DC-71): adaptador de OpenStreetMap con Leaflet para el mapa en vivo del panel, con las mismas propiedades
 * que `MapaGoogle` y el esquemático. Los marcadores llevan el mismo color por estado, la patente y la selección.
 */
export function MapaOsm({ conductores, seleccionado, alSeleccionar, ahora, alFallar, reencuadrar = 0, enfoque = 0 }: Props) {
  const elemento = useRef<HTMLDivElement>(null);
  const [listo, setListo] = useState<{ leaflet: L; mapa: Leaflet.Map } | null>(null);
  const marcadores = useRef(new Map<number, Leaflet.CircleMarker>());
  const encuadrado = useRef(false);
  const seleccionar = useRef(alSeleccionar);
  const fallar = useRef(alFallar);
  const ultimos = useRef(conductores);
  useEffect(() => {
    seleccionar.current = alSeleccionar;
    fallar.current = alFallar;
    ultimos.current = conductores;
  });

  useEffect(() => {
    let vigente = true;
    let mapa: Leaflet.Map | null = null;
    cargarLeaflet().then(
      (leaflet) => {
        if (!vigente || !elemento.current) return;
        const zona = encuadre([]);
        mapa = leaflet.map(elemento.current).setView([(zona.latMin + zona.latMax) / 2, (zona.lonMin + zona.lonMax) / 2], 11);
        capaOsm(leaflet, () => fallar.current()).addTo(mapa);
        setListo({ leaflet, mapa });
      },
      () => {
        if (vigente) fallar.current();
      },
    );
    return () => {
      vigente = false;
      mapa?.remove();
    };
  }, []);

  // Crea, actualiza y quita marcadores en vez de redibujar: el mapa no parpadea con cada posición.
  useEffect(() => {
    if (!listo) return;
    const { leaflet, mapa } = listo;
    const vivos = new Set<number>();
    for (const conductor of conductores) {
      const datos = datosMarcador(conductor, seleccionado, ahora);
      if (!datos) continue;
      vivos.add(conductor.id);
      let marcador = marcadores.current.get(conductor.id);
      if (!marcador) {
        marcador = leaflet.circleMarker([datos.posicion.lat, datos.posicion.lng], estilo(datos));
        marcador.bindTooltip(datos.etiqueta, { permanent: true, direction: 'right', offset: [8, 0] });
        marcador.on('click', () => seleccionar.current(conductor.id));
        marcador.addTo(mapa);
        marcadores.current.set(conductor.id, marcador);
      }
      aplicar(marcador, datos);
    }
    for (const [id, marcador] of marcadores.current) {
      if (vivos.has(id)) continue;
      marcador.remove();
      marcadores.current.delete(id);
    }
    // Encuadra una vez: después, quien mira el mapa decide el zoom.
    if (!encuadrado.current && vivos.size > 0) {
      const zona = encuadre(conductores);
      mapa.fitBounds([
        [zona.latMin, zona.lonMin],
        [zona.latMax, zona.lonMax],
      ]);
      encuadrado.current = true;
    }
  }, [listo, conductores, seleccionado, ahora]);

  useEffect(() => {
    if (!listo || !elemento.current || typeof ResizeObserver === 'undefined') return;
    const observador = new ResizeObserver(() => {
      if (typeof listo.mapa.invalidateSize === 'function') listo.mapa.invalidateSize();
    });
    observador.observe(elemento.current);
    return () => observador.disconnect();
  }, [listo]);

  useEffect(() => {
    if (!listo || reencuadrar === 0) return;
    const conPosicion = ultimos.current.filter((c) => c.posicion);
    if (!conPosicion.length) return;
    const zona = encuadre(conPosicion);
    listo.mapa.fitBounds(
      [
        [zona.latMin, zona.lonMin],
        [zona.latMax, zona.lonMax],
      ],
      { padding: [32, 32] },
    );
  }, [listo, reencuadrar]);

  useEffect(() => {
    if (!listo || seleccionado === null) return;
    const posicion = ultimos.current.find((c) => c.id === seleccionado)?.posicion;
    if (!posicion) return;
    if (typeof listo.mapa.flyTo === 'function' && typeof listo.mapa.getZoom === 'function') {
      listo.mapa.flyTo([posicion.lat, posicion.lon], Math.max(listo.mapa.getZoom(), 15), { duration: 0.6 });
    } else {
      listo.mapa.panTo([posicion.lat, posicion.lon]);
    }
  }, [listo, seleccionado, enfoque]);

  return <div ref={elemento} className={estilos.mapaGoogle} role="region" aria-label="Mapa de conductores en turno" />;
}

function estilo(datos: DatosMarcador): Leaflet.CircleMarkerOptions {
  return { radius: datos.escala, fillColor: datos.color, fillOpacity: datos.opacidad, color: '#ffffff', weight: 2, opacity: 1 };
}

function aplicar(marcador: Leaflet.CircleMarker, datos: DatosMarcador) {
  marcador.setLatLng([datos.posicion.lat, datos.posicion.lng]);
  marcador.setStyle(estilo(datos));
  marcador.setRadius(datos.escala);
  marcador.setTooltipContent(datos.etiqueta);
  // El seleccionado queda encima, como el zIndex en Google.
  if (datos.seleccionado) marcador.bringToFront();
}
