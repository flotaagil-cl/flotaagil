import type * as Leaflet from 'leaflet';
import { useEffect, useRef, useState } from 'react';
import { ICONOS } from '../diseno/iconos';
import { MapaRespaldo } from '../diseno/mapa/MapaRespaldo';
import type { Marcador, PropsMapa } from '../diseno/mapa/tipos';
import c from './mapaOsm.module.css';
import { capaOsm, cargarLeaflet } from './osm';

const ICONO_DE: Record<Marcador['tipo'], keyof typeof ICONOS | null> = {
  aeropuerto: 'avion',
  origen: 'usuario',
  vehiculo: 'auto',
  destino: null,
};

function htmlDelPin(marcador: Marcador): string {
  const icono = ICONO_DE[marcador.tipo];
  const dibujo = icono ? `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONOS[icono]}"/></svg>` : '';
  return `<span class="${c.pin}" data-tipo="${marcador.tipo}">${dibujo}</span>`;
}

/**
 * HU-70 (DC-71): mapa de OpenStreetMap para las pantallas del portal (`<Mapa>` de diseno/mapa), con las mismas
 * propiedades que el de respaldo. Si Leaflet o las teselas no cargan, muestra el de respaldo.
 */
export function MapaOsmPortal(props: PropsMapa) {
  const [falla, setFalla] = useState(false);
  if (falla) return <MapaRespaldo {...props} />;
  return <MapaLeaflet {...props} alFallar={() => setFalla(true)} />;
}

/** Centro de Santiago: la vista sin pines (al abrir y al volver a «En la ciudad» sin direcciones). */
const SANTIAGO: [number, number] = [-33.45, -70.66];
const ZOOM_SANTIAGO = 11;

function MapaLeaflet({ etiqueta, marcadores, ruta, alFallar }: PropsMapa & { alFallar: () => void }) {
  const elemento = useRef<HTMLDivElement>(null);
  const [listo, setListo] = useState<{ leaflet: typeof Leaflet; mapa: Leaflet.Map } | null>(null);
  const fallar = useRef(alFallar);
  useEffect(() => {
    fallar.current = alFallar;
  });

  useEffect(() => {
    let vigente = true;
    let mapa: Leaflet.Map | null = null;
    cargarLeaflet().then(
      (leaflet) => {
        if (!vigente || !elemento.current) return;
        mapa = leaflet.map(elemento.current, { zoomControl: false }).setView(SANTIAGO, ZOOM_SANTIAGO);
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

  // Pines y ruta: se rehacen cuando cambian (son pocos y el portal los actualiza poco).
  useEffect(() => {
    if (!listo) return;
    const { leaflet, mapa } = listo;
    const capa = leaflet.layerGroup().addTo(mapa);
    const acento = getComputedStyle(document.documentElement).getPropertyValue('--acento').trim() || '#0e7c7b';
    if (ruta) {
      leaflet
        .polyline(
          [
            [ruta.desde.lat, ruta.desde.lng],
            [ruta.hasta.lat, ruta.hasta.lng],
          ],
          { color: acento, weight: 4, dashArray: '8 8' },
        )
        .addTo(capa);
    }
    for (const marcador of marcadores) {
      const icono = leaflet.divIcon({ html: htmlDelPin(marcador), className: c.contenedorPin, iconSize: [32, 32], iconAnchor: [16, 16] });
      leaflet.marker([marcador.punto.lat, marcador.punto.lng], { icon: icono, title: marcador.etiqueta, alt: marcador.etiqueta, keyboard: false }).addTo(capa);
    }
    const puntos: [number, number][] = [
      ...marcadores.map((m): [number, number] => [m.punto.lat, m.punto.lng]),
      ...(ruta ? [[ruta.desde.lat, ruta.desde.lng] as [number, number], [ruta.hasta.lat, ruta.hasta.lng] as [number, number]] : []),
    ];
    if (puntos.length > 1) mapa.fitBounds(puntos, { padding: [40, 40], maxZoom: 15 });
    else if (puntos.length === 1) mapa.setView(puntos[0], 15);
    else mapa.setView(SANTIAGO, ZOOM_SANTIAGO); // sin pines no se queda en el último encuadre
    return () => {
      capa.remove();
    };
  }, [listo, marcadores, ruta]);

  return <div ref={elemento} className={c.mapa} role="region" aria-label={etiqueta} />;
}
