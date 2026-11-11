import { useEffect, useId, useRef, type ReactNode } from 'react';
import e from './diseno.module.css';
import { Icono } from './Icono';

interface Props {
  abierto: boolean;
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
  /** «menu»: se abre arriba a la derecha (menú de la cuenta); «centrado»: confirmaciones. */
  variante?: 'centrado' | 'menu';
}

const ENFOCABLES = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Diálogo modal: aria-modal, cierre con Esc, con el botón Cerrar o tocando fuera. Al abrir enfoca el primer
 * control, el Tab no sale del diálogo y al cerrar el foco vuelve a donde estaba.
 */
export function Dialogo({ abierto, titulo, onCerrar, children, variante = 'centrado' }: Props) {
  const id = useId();
  const caja = useRef<HTMLDivElement>(null);
  const cerrar = useRef(onCerrar);
  useEffect(() => {
    cerrar.current = onCerrar;
  });

  useEffect(() => {
    if (!abierto) return;
    const previo = document.activeElement as HTMLElement | null;
    const enfocables = () => Array.from(caja.current?.querySelectorAll<HTMLElement>(ENFOCABLES) ?? []);
    (enfocables()[1] ?? enfocables()[0] ?? caja.current)?.focus();

    function tecla(evento: KeyboardEvent) {
      if (evento.key === 'Escape') {
        evento.preventDefault();
        cerrar.current();
        return;
      }
      if (evento.key !== 'Tab') return;
      const lista = enfocables();
      if (!lista.length) return;
      const primero = lista[0];
      const ultimo = lista[lista.length - 1];
      if (evento.shiftKey && document.activeElement === primero) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primero.focus();
      }
    }
    document.addEventListener('keydown', tecla);
    return () => {
      document.removeEventListener('keydown', tecla);
      previo?.focus();
    };
  }, [abierto]);

  if (!abierto) return null;
  return (
    <div
      className={e.fondoDialogo}
      data-variante={variante}
      onMouseDown={(evento) => {
        if (evento.target === evento.currentTarget) onCerrar();
      }}
    >
      <div ref={caja} role="dialog" aria-modal="true" aria-labelledby={`${id}-titulo`} className={e.dialogo} tabIndex={-1}>
        <div className={e.dialogoCabecera}>
          <h2 id={`${id}-titulo`} className={e.dialogoTitulo}>
            {titulo}
          </h2>
          <button type="button" className={e.dialogoCerrar} aria-label="Cerrar" onClick={onCerrar}>
            <Icono nombre="cerrar" />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
