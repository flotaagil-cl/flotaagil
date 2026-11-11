import type { ReactNode } from 'react';
import { Link } from 'react-router';
import e from './diseno.module.css';
import { Icono } from './Icono';

interface Props {
  /** El mapa (normalmente <Mapa>). */
  mapa: ReactNode;
  /** Botón para volver (solo en el celular, donde no están las pestañas). */
  volver?: { a: string; texto: string };
  /** Etiqueta sobre el mapa, arriba a la derecha («SCL · Llegadas»). */
  estado?: ReactNode;
  children: ReactNode;
}

/**
 * Pantalla con mapa: en el computador el contenido va a la izquierda y el mapa en una tarjeta a la derecha;
 * en el celular el mapa queda arriba y el contenido en un panel inferior que lo cubre en parte. El contenido va
 * primero en el documento, así el lector de pantalla y el teclado llegan directo al formulario.
 */
export function PantallaConMapa({ mapa, volver, estado, children }: Props) {
  return (
    <div className={e.conMapa}>
      <div className={e.panel}>
        <span className={e.asa} aria-hidden="true" />
        {children}
      </div>
      <div className={e.zonaMapa}>
        {mapa}
        {volver && (
          <Link to={volver.a} className={e.volver} aria-label={volver.texto}>
            <Icono nombre="atras" />
          </Link>
        )}
        {estado && <span className={e.chipMapa}>{estado}</span>}
      </div>
    </div>
  );
}
