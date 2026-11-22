// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { DeslizarParaActualizar, UMBRAL_PX } from './DeslizarParaActualizar';

afterEach(() => {
  cleanup();
  Object.defineProperty(window, 'scrollY', { value: 0, configurable: true });
});

function arrastrar(nodo: Element, desde: number, hasta: number, cancelar = false) {
  fireEvent.touchStart(nodo, { touches: [{ clientY: desde }] });
  fireEvent.touchMove(nodo, { touches: [{ clientY: hasta }] });
  if (cancelar) fireEvent.touchCancel(nodo);
  else fireEvent.touchEnd(nodo);
}

describe('DeslizarParaActualizar', () => {
  it('actualiza al arrastrar hacia abajo por encima del umbral y limpia el estado al terminar', async () => {
    let resolver!: () => void;
    const alActualizar = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolver = resolve;
        }),
    );
    const { container } = render(
      <DeslizarParaActualizar alActualizar={alActualizar}>
        <p>Contenido</p>
      </DeslizarParaActualizar>,
    );
    const zona = container.firstElementChild!;

    // Con fricción 0.5 se necesitan > 2 * UMBRAL_PX para cruzar el umbral.
    arrastrar(zona, 0, UMBRAL_PX * 2 + 20);
    expect(alActualizar).toHaveBeenCalledOnce();
    expect(zona.getAttribute('aria-busy')).toBe('true');
    expect(screen.getByText('Actualizando…')).toBeTruthy();

    await act(async () => {
      resolver();
    });
    expect(zona.getAttribute('aria-busy')).toBe('false');
  });

  it('no actualiza si el arrastre es corto, si se cancela, si sube o si la página ya bajó', () => {
    const alActualizar = vi.fn(async () => {});
    const { container } = render(
      <DeslizarParaActualizar alActualizar={alActualizar}>
        <p>Contenido</p>
      </DeslizarParaActualizar>,
    );
    const zona = container.firstElementChild!;

    arrastrar(zona, 0, 40);
    arrastrar(zona, 100, 40);
    arrastrar(zona, 0, 200, true);
    Object.defineProperty(window, 'scrollY', { value: 120, configurable: true });
    arrastrar(zona, 0, 200);

    expect(alActualizar).not.toHaveBeenCalled();
  });
});
