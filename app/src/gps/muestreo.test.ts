import { describe, expect, it } from 'vitest';
import { debeRegistrar, INTERVALO_OBJETIVO_S, MARGEN_MS } from './muestreo';

describe('debeRegistrar', () => {
  it('la primera entrega siempre se registra', () => {
    expect(debeRegistrar(null, 1_000, 10)).toBe(true);
  });

  it('respeta el intervalo con la tolerancia', () => {
    expect(debeRegistrar(0, 10_000 - MARGEN_MS - 1, 10)).toBe(false);
    expect(debeRegistrar(0, 10_000 - MARGEN_MS, 10)).toBe(true);
  });

  it('10 s en viaje y 30 s en espera', () => {
    expect(INTERVALO_OBJETIVO_S).toEqual({ viaje: 10, espera: 30 });
    expect(debeRegistrar(0, 20_000, INTERVALO_OBJETIVO_S.espera)).toBe(false);
  });
});
