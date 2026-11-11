import type { ReactNode } from 'react';
import e from './diseno.module.css';
import { Icono } from './Icono';
import type { NombreIcono } from './iconos';

export type TonoInsignia = 'info' | 'ok' | 'revision' | 'peligro' | 'neutra';

/** Insignia de estado. El texto dice el estado: el color solo lo refuerza. */
export function Insignia({ tono = 'info', children }: { tono?: TonoInsignia; children: ReactNode }) {
  return (
    <span className={e.insignia} data-tono={tono}>
      {children}
    </span>
  );
}

interface PropsTarjeta {
  como?: 'section' | 'div' | 'article';
  className?: string;
  children: ReactNode;
  'aria-labelledby'?: string;
}

export function Tarjeta({ como: Etiqueta = 'div', className, children, ...resto }: PropsTarjeta) {
  return (
    <Etiqueta className={[e.tarjeta, className].filter(Boolean).join(' ')} {...resto}>
      {children}
    </Etiqueta>
  );
}

interface PropsDestacado {
  titulo: string;
  icono?: NombreIcono;
  children?: ReactNode;
}

/** Franja con el degradé destacado (por ejemplo, «Seguimos tu vuelo por ti»). */
export function Destacado({ titulo, icono = 'avion', children }: PropsDestacado) {
  return (
    <div className={e.destacado}>
      <span className={e.destacadoIcono}>
        <Icono nombre={icono} />
      </span>
      <div>
        <p className={e.destacadoTitulo}>{titulo}</p>
        {children && <p className={e.destacadoTexto}>{children}</p>}
      </div>
    </div>
  );
}

export function Avatar({ texto }: { texto: string }) {
  return (
    <span className={e.avatar} aria-hidden="true">
      {texto}
    </span>
  );
}
