import { confianza, encuadre, type ConductorMapa } from './estado';
import estilos from './mapa.module.css';

const ANCHO = 1000;
const ALTO = 640;

interface Props {
  conductores: ConductorMapa[];
  seleccionado: number | null;
  alSeleccionar: (id: number) => void;
  ahora: number;
}

/**
 * Adaptador de desarrollo del mapa (HU-02): dibuja los conductores sobre una cuadrícula proyectada a partir de sus
 * coordenadas, sin servicios externos ni claves. Con `VITE_GOOGLE_MAPS_KEY` se usará Google Maps JS (PR-12) con
 * las mismas propiedades. Los marcadores también están en la lista accesible de la página.
 */
export function MapaEsquematico({ conductores, seleccionado, alSeleccionar, ahora }: Props) {
  const zona = encuadre(conductores);
  const x = (lon: number) => ((lon - zona.lonMin) / (zona.lonMax - zona.lonMin)) * ANCHO;
  const y = (lat: number) => ((zona.latMax - lat) / (zona.latMax - zona.latMin)) * ALTO;
  const lineas = Array.from({ length: 9 }, (_, i) => i / 8);

  return (
    <svg className={estilos.mapa} viewBox={`0 0 ${ANCHO} ${ALTO}`} role="img" aria-label="Mapa de conductores en turno">
      <rect width={ANCHO} height={ALTO} className={estilos.fondo} />
      {lineas.map((f) => (
        <g key={f} className={estilos.cuadricula}>
          <line x1={f * ANCHO} y1={0} x2={f * ANCHO} y2={ALTO} />
          <line x1={0} y1={f * ALTO} x2={ANCHO} y2={f * ALTO} />
        </g>
      ))}
      {conductores.map((conductor) => {
        if (!conductor.posicion) return null;
        const { confiable } = confianza(conductor, ahora);
        const activo = conductor.id === seleccionado;
        return (
          <g
            key={conductor.id}
            transform={`translate(${x(conductor.posicion.lon)} ${y(conductor.posicion.lat)})`}
            className={estilos.marcador}
            data-estado={conductor.estado}
            data-confiable={confiable}
            data-seleccionado={activo || undefined}
            onClick={() => alSeleccionar(conductor.id)}
            aria-hidden="true"
          >
            <circle r={activo ? 16 : 12} />
            <text y={-20} textAnchor="middle">
              {conductor.patente ?? conductor.nombre.split(' ')[0]}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
