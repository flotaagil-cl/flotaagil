import { describe, expect, it } from 'vitest';
import { leerMonto, metodosDePago, pasoSiguiente } from './ejecucion';

describe('pasos del viaje', () => {
  it('siguen la secuencia y terminan en el pago', () => {
    expect(pasoSiguiente('ACEPTADO')?.accion).toBe('en-camino');
    expect(pasoSiguiente('EN_CAMINO')?.accion).toBe('a-bordo');
    expect(pasoSiguiente('EN_ZONA')?.accion).toBe('a-bordo');
    expect(pasoSiguiente('PASAJERO_A_BORDO')).toBeNull();
  });
});

describe('método de pago', () => {
  it('ofrece Convenio solo en viajes de convenio', () => {
    expect(metodosDePago(false).map((m) => m.valor)).toEqual(['EFECTIVO', 'TARJETA', 'TRANSFERENCIA']);
    expect(metodosDePago(true)[0].valor).toBe('CONVENIO');
  });
});

describe('monto', () => {
  it.each([
    ['15000', 15000],
    ['15.000', 15000],
    [' $15.000 ', 15000],
    ['0', 0],
    ['500000', 500000],
  ])('acepta %s', (texto, monto) => {
    expect(leerMonto(texto)).toEqual({ monto });
  });

  it.each(['', '   ', '-1', '15000,5', 'abc', '500001'])('rechaza «%s»', (texto) => {
    expect(leerMonto(texto).error).toBeTruthy();
  });
});
