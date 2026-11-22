import { useRef, useState, type ReactNode, type TouchEvent } from 'react';

/** Cuánto hay que arrastrar (ya con fricción) para que al soltar se actualice. */
export const UMBRAL_PX = 64;
const MAXIMO_PX = 96;
const FRICCION = 0.5;
const ALTO_ACTUALIZANDO_PX = 48;

interface Props {
  /** Recarga lo que muestra la pantalla; el indicador gira hasta que termina (bien o mal). */
  alActualizar: () => Promise<unknown>;
  children: ReactNode;
}

/**
 * Deslizar hacia abajo para actualizar (pull-to-refresh táctil). Solo arranca con la página arriba del todo. El
 * indicador queda arriba del contenido; `overscroll-behavior` (estilos.css) evita el rebote nativo del WebView.
 */
export function DeslizarParaActualizar({ alActualizar, children }: Props) {
  const [distancia, setDistancia] = useState(0);
  const [actualizando, setActualizando] = useState(false);
  const inicio = useRef<number | null>(null);

  function alTocar(evento: TouchEvent) {
    inicio.current = !actualizando && window.scrollY <= 0 ? evento.touches[0].clientY : null;
  }

  function alMover(evento: TouchEvent) {
    if (inicio.current === null) return;
    const arrastre = evento.touches[0].clientY - inicio.current;
    if (arrastre <= 0 || window.scrollY > 0) {
      inicio.current = null;
      setDistancia(0);
      return;
    }
    setDistancia(Math.min(MAXIMO_PX, arrastre * FRICCION));
  }

  function cancelar() {
    inicio.current = null;
    setDistancia(0);
  }

  async function alSoltar() {
    if (inicio.current === null) return;
    inicio.current = null;
    if (distancia < UMBRAL_PX) {
      setDistancia(0);
      return;
    }
    setDistancia(0);
    setActualizando(true);
    try {
      await alActualizar();
    } finally {
      setActualizando(false);
    }
  }

  const alto = actualizando ? ALTO_ACTUALIZANDO_PX : distancia;

  return (
    <div className="tirar" aria-busy={actualizando} onTouchStart={alTocar} onTouchMove={alMover} onTouchEnd={() => void alSoltar()} onTouchCancel={cancelar}>
      <div className={`tirar-indicador${distancia === 0 ? ' suelto' : ''}`} aria-hidden="true" style={{ height: alto }}>
        {alto > 0 && <span className={`tirar-giro${actualizando ? ' girando' : ''}`} style={{ opacity: actualizando ? 1 : Math.min(1, alto / UMBRAL_PX) }} />}
      </div>
      <div className="solo-lector" aria-live="polite">
        {actualizando ? 'Actualizando…' : ''}
      </div>
      {children}
    </div>
  );
}
