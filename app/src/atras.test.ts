import { describe, expect, it, vi } from 'vitest';
import { manejarAtras, registrarAtras } from './atras';

describe('pila del botón Atrás', () => {
  it('devuelve false si no hay ninguna pantalla secundaria registrada', () => {
    expect(manejarAtras()).toBe(false);
  });

  it('ejecuta el último manejador registrado y al quitarlo vuelve al anterior', () => {
    const primero = vi.fn();
    const segundo = vi.fn();
    const quitarPrimero = registrarAtras(primero);
    const quitarSegundo = registrarAtras(segundo);

    expect(manejarAtras()).toBe(true);
    expect(segundo).toHaveBeenCalledOnce();
    expect(primero).not.toHaveBeenCalled();

    quitarSegundo();
    expect(manejarAtras()).toBe(true);
    expect(primero).toHaveBeenCalledOnce();

    quitarPrimero();
    expect(manejarAtras()).toBe(false);
  });
});
