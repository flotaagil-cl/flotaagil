/**
 * El plugin entrega posiciones cada ~1 s (intervalo fijo de 1000 ms en su servicio Android, con distanceFilter 0;
 * ver docs/poc-gps.md, A2). La app registra solo una cada 10 s en viaje o 30 s en espera. Se decide en cada
 * entrega del plugin y no con temporizadores, porque los temporizadores de JavaScript se ralentizan con la app
 * en segundo plano.
 */

export type Modo = 'viaje' | 'espera';

/** Intervalo objetivo entre posiciones registradas (H-3). */
export const INTERVALO_OBJETIVO_S: Record<Modo, number> = { viaje: 10, espera: 30 };

/** Tolerancia para no saltarse una muestra cuando la entrega llega levemente antes del objetivo. */
export const MARGEN_MS = 500;

export function debeRegistrar(ultimaMs: number | null, ahoraMs: number, objetivoS: number): boolean {
  return ultimaMs === null || ahoraMs - ultimaMs >= objetivoS * 1000 - MARGEN_MS;
}
