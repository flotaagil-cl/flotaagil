import type { Punto } from './tipos';

export const ANCHO = 400;
export const ALTO = 300;
/** Márgenes del área útil: el mapa se recorta al llenar contenedores más altos o más anchos que 4:3. */
const MARGEN_X = 90;
const MARGEN_Y = 60;

/**
 * Proyección simple para el mapa de respaldo: encuadra los puntos dados en el área útil del lienzo,
 * conserva la proporción y deja el norte arriba. No es cartografía: solo ubica los pines entre sí.
 */
export function proyectar(puntos: Punto[]): (p: Punto) => { x: number; y: number } {
  if (!puntos.length) return () => ({ x: ANCHO / 2, y: ALTO / 2 });
  const lats = puntos.map((p) => p.lat);
  const lngs = puntos.map((p) => p.lng);
  const [minLat, maxLat, minLng, maxLng] = [Math.min(...lats), Math.max(...lats), Math.min(...lngs), Math.max(...lngs)];
  const anchoUtil = ANCHO - 2 * MARGEN_X;
  const altoUtil = ALTO - 2 * MARGEN_Y;
  const escala = Math.min(anchoUtil / (maxLng - minLng || 1e-9), altoUtil / (maxLat - minLat || 1e-9));
  const centroLng = (minLng + maxLng) / 2;
  const centroLat = (minLat + maxLat) / 2;
  const unico = maxLng === minLng && maxLat === minLat;
  return (p) =>
    unico
      ? { x: ANCHO / 2, y: ALTO / 2 }
      : { x: ANCHO / 2 + (p.lng - centroLng) * escala, y: ALTO / 2 - (p.lat - centroLat) * escala };
}

/** Curva suave entre dos puntos (como la ruta del diseño). */
export function curva(a: { x: number; y: number }, b: { x: number; y: number }): string {
  const control = { x: (a.x + b.x) / 2 + (b.y - a.y) * 0.2, y: (a.y + b.y) / 2 - (b.x - a.x) * 0.2 };
  const r = (n: number) => Math.round(n * 10) / 10;
  return `M${r(a.x)} ${r(a.y)} Q${r(control.x)} ${r(control.y)} ${r(b.x)} ${r(b.y)}`;
}
