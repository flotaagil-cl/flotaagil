import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react';
import e from './diseno.module.css';

export interface Pestana {
  id: string;
  titulo: string;
}

interface Props {
  etiqueta: string;
  pestanas: Pestana[];
  activa: string;
  onCambiar: (id: string) => void;
  children: ReactNode;
}

/** Pestañas con el patrón ARIA: flechas, Inicio y Fin mueven entre ellas y la activa es la única tabulable. */
export function Pestanas({ etiqueta, pestanas, activa, onCambiar, children }: Props) {
  const base = useId();
  const lista = useRef<HTMLDivElement>(null);

  function teclado(evento: KeyboardEvent) {
    const actual = pestanas.findIndex((p) => p.id === activa);
    const destino = {
      ArrowRight: (actual + 1) % pestanas.length,
      ArrowLeft: (actual - 1 + pestanas.length) % pestanas.length,
      Home: 0,
      End: pestanas.length - 1,
    }[evento.key];
    if (destino === undefined) return;
    evento.preventDefault();
    onCambiar(pestanas[destino].id);
    lista.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]')[destino]?.focus();
  }

  return (
    <div>
      <div ref={lista} role="tablist" aria-label={etiqueta} className={e.pestanas} onKeyDown={teclado}>
        {pestanas.map((p) => (
          <button
            key={p.id}
            type="button"
            role="tab"
            id={`${base}-${p.id}`}
            aria-selected={p.id === activa}
            aria-controls={`${base}-panel`}
            tabIndex={p.id === activa ? 0 : -1}
            className={e.pestana}
            onClick={() => onCambiar(p.id)}
          >
            {p.titulo}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${base}-panel`} aria-labelledby={`${base}-${activa}`} className={e.panelPestana}>
        {children}
      </div>
    </div>
  );
}
