import { useEffect, useRef, useState } from 'react';
import { encuadre, type ConductorMapa } from './estado';
import { alRechazarClave, cargarGoogleMaps, datosMarcador, type DatosMarcador, type GoogleMaps, type MapaGoogleApi, type MarcadorGoogle } from './googleMaps';
import estilos from './mapa.module.css';

interface Props {
  clave: string;
  conductores: ConductorMapa[];
  seleccionado: number | null;
  alSeleccionar: (id: number) => void;
  ahora: number;
  /** No se pudo cargar o Google rechazó la clave: quien lo usa vuelve al mapa esquemático. */
  alFallar: () => void;
}

/** Adaptador de Google Maps JS (PR-12), con las mismas propiedades que el esquemático. */
export function MapaGoogle({ clave, conductores, seleccionado, alSeleccionar, ahora, alFallar }: Props) {
  const elemento = useRef<HTMLDivElement>(null);
  const [lista, setLista] = useState<{ api: GoogleMaps; mapa: MapaGoogleApi } | null>(null);
  const marcadores = useRef(new Map<number, MarcadorGoogle>());
  const encuadrado = useRef(false);
  const seleccionar = useRef(alSeleccionar);
  const fallar = useRef(alFallar);
  // Elegir en la lista lleva al conductor, solo al cambiar la selección: las posiciones se leen de esta referencia.
  const ultimos = useRef(conductores);
  useEffect(() => {
    seleccionar.current = alSeleccionar;
    fallar.current = alFallar;
    ultimos.current = conductores;
  });

  useEffect(() => {
    let vigente = true;
    const quitar = alRechazarClave(() => fallar.current());
    cargarGoogleMaps(clave).then(
      (api) => {
        if (!vigente || !elemento.current) return;
        const zona = encuadre([]);
        const mapa = new api.Map(elemento.current, {
          center: { lat: (zona.latMin + zona.latMax) / 2, lng: (zona.lonMin + zona.lonMax) / 2 },
          zoom: 11,
          mapTypeControl: false,
          streetViewControl: false,
        });
        setLista({ api, mapa });
      },
      () => {
        if (vigente) fallar.current();
      },
    );
    return () => {
      vigente = false;
      quitar();
    };
  }, [clave]);

  // Crea, actualiza y quita marcadores en vez de redibujar: el mapa no parpadea con cada posición.
  useEffect(() => {
    if (!lista) return;
    const { api, mapa } = lista;
    const vivos = new Set<number>();
    for (const conductor of conductores) {
      const datos = datosMarcador(conductor, seleccionado, ahora);
      if (!datos) continue;
      vivos.add(conductor.id);
      let marcador = marcadores.current.get(conductor.id);
      if (!marcador) {
        marcador = new api.Marker({ map: mapa });
        marcador.addListener('click', () => seleccionar.current(conductor.id));
        marcadores.current.set(conductor.id, marcador);
      }
      aplicar(marcador, datos, api);
    }
    for (const [id, marcador] of marcadores.current) {
      if (vivos.has(id)) continue;
      marcador.setMap(null);
      marcadores.current.delete(id);
    }
    // Encuadra una vez: después, quien mira el mapa decide el zoom y no se le mueve con cada posición.
    if (!encuadrado.current && vivos.size > 0) {
      const zona = encuadre(conductores);
      const limites = new api.LatLngBounds();
      limites.extend({ lat: zona.latMin, lng: zona.lonMin });
      limites.extend({ lat: zona.latMax, lng: zona.lonMax });
      mapa.fitBounds(limites);
      encuadrado.current = true;
    }
  }, [lista, conductores, seleccionado, ahora]);

  useEffect(() => {
    if (!lista || seleccionado === null) return;
    const posicion = ultimos.current.find((c) => c.id === seleccionado)?.posicion;
    if (posicion) lista.mapa.panTo({ lat: posicion.lat, lng: posicion.lon });
  }, [lista, seleccionado]);

  useEffect(() => {
    const creados = marcadores.current;
    return () => {
      creados.forEach((marcador) => marcador.setMap(null));
      creados.clear();
    };
  }, []);

  return <div ref={elemento} className={estilos.mapaGoogle} role="region" aria-label="Mapa de conductores en turno" />;
}

function aplicar(marcador: MarcadorGoogle, datos: DatosMarcador, api: GoogleMaps) {
  marcador.setPosition(datos.posicion);
  marcador.setTitle(datos.titulo);
  marcador.setLabel({ text: datos.etiqueta, fontWeight: '600', fontSize: '12px', color: '#111827' });
  marcador.setZIndex(datos.seleccionado ? 2 : 1);
  marcador.setIcon({
    path: api.SymbolPath.CIRCLE,
    scale: datos.escala,
    fillColor: datos.color,
    fillOpacity: datos.opacidad,
    strokeColor: '#ffffff',
    strokeWeight: 2,
  });
}
