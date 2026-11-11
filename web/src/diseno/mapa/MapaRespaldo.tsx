import e from '../diseno.module.css';
import { ICONOS } from '../iconos';
import { ALTO, ANCHO, curva, proyectar } from './proyeccion';
import type { Marcador, PropsMapa } from './tipos';

/** Calles y parques decorativos (fijos), más largos que el lienzo para cubrirlo al recortarse. */
const CALLES = ['M-100 95 L500 35', 'M-100 230 L500 265', 'M95 -100 L70 400', 'M265 -100 L290 400', 'M-100 160 L500 120'];
const PARQUES = [
  { x: 150, y: 120, w: 70, h: 50 },
  { x: 310, y: 50, w: 60, h: 45 },
  { x: 20, y: 250, w: 60, h: 40 },
];

/**
 * Mapa de respaldo: un plano esquemático en SVG con los pines y la ruta, sin servicios externos. Se usa
 * mientras no esté el mapa real y si este no carga. Los colores salen de los tokens del portal.
 */
export function MapaRespaldo({ etiqueta, marcadores, ruta }: PropsMapa) {
  const puntos = [...marcadores.map((m) => m.punto), ...(ruta ? [ruta.desde, ruta.hasta] : [])];
  const ubicar = proyectar(puntos);
  return (
    <svg className={e.mapa} viewBox={`0 0 ${ANCHO} ${ALTO}`} preserveAspectRatio="xMidYMid slice" role="img" aria-label={etiqueta}>
      <rect className={e.mapaFondo} x={-200} y={-200} width={ANCHO + 400} height={ALTO + 400} />
      {PARQUES.map((p) => (
        <rect key={`${p.x}-${p.y}`} className={e.mapaParque} x={p.x} y={p.y} width={p.w} height={p.h} rx={8} />
      ))}
      {CALLES.map((d) => (
        <path key={d} className={e.mapaCalle} d={d} />
      ))}
      {ruta && <path className={e.mapaRuta} d={curva(ubicar(ruta.desde), ubicar(ruta.hasta))} />}
      {marcadores.map((m) => (
        <Pin key={m.id} marcador={m} {...ubicar(m.punto)} />
      ))}
    </svg>
  );
}

function Pin({ marcador, x, y }: { marcador: Marcador; x: number; y: number }) {
  if (marcador.tipo === 'destino') {
    return (
      <g data-tipo="destino">
        <title>{marcador.etiqueta}</title>
        <rect className={e.pinPrincipal} x={x - 10} y={y - 10} width={20} height={20} rx={3} />
      </g>
    );
  }
  if (marcador.tipo === 'vehiculo') {
    return (
      <g data-tipo="vehiculo">
        <title>{marcador.etiqueta}</title>
        <circle className={e.pinVehiculo} cx={x} cy={y} r={13} />
        <svg x={x - 8} y={y - 8} width={16} height={16} viewBox="0 0 24 24" className={e.pinVehiculoIcono}>
          <path d={ICONOS.auto} />
        </svg>
      </g>
    );
  }
  return (
    <g data-tipo={marcador.tipo}>
      <title>{marcador.etiqueta}</title>
      <circle className={e.pinPrincipal} cx={x} cy={y} r={16} />
      <svg x={x - 8} y={y - 8} width={16} height={16} viewBox="0 0 24 24" className={e.pinIcono}>
        <path d={marcador.tipo === 'aeropuerto' ? ICONOS.avion : ICONOS.usuario} />
      </svg>
    </g>
  );
}
