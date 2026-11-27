import type { ReactNode } from 'react';
import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { mensajeDeError } from '../errores';
import s from '../flota.module.css';

/** Celda con su título: en celular la tabla pasa a tarjetas y el título va a la izquierda (CSS). */
export function Celda({ titulo, children, className }: { titulo: string; children: ReactNode; className?: string }) {
  return (
    <td data-titulo={titulo} className={className}>
      <div>{children}</div>
    </td>
  );
}

/** Error de una consulta con «Reintentar». */
export function FallaDeCarga({ error, que, reintentar }: { error: unknown; que: string; reintentar: () => void }) {
  return (
    <div className={s.vacio} role="alert">
      <div className={s.iconoVacio} aria-hidden="true">
        <Icono nombre="alerta" tamano={24} />
      </div>
      <p>{mensajeDeError(error, que)}</p>
      <button type="button" className={estilos.boton} onClick={reintentar}>
        Reintentar
      </button>
    </div>
  );
}

export function NoEncontrado({ que, volverA, texto }: { que: string; volverA: string; texto: string }) {
  return (
    <section>
      <div className={s.vacio}>
        <div className={s.iconoVacio} aria-hidden="true">
          <Icono nombre="info" tamano={24} />
        </div>
        <h1>No encontrado</h1>
        <p>No existe {que} o no es de tu empresa.</p>
        <Link to={volverA} className={estilos.botonSecundario}>
          {texto}
        </Link>
      </div>
    </section>
  );
}

/** Filas de espera de una tabla mientras llega la primera página. */
export function Esqueleto({ etiqueta, columnas }: { etiqueta: string; columnas: number }) {
  return (
    <div className={s.contenedorTabla}>
      <table className={s.tablaFlota} aria-busy="true" aria-label={etiqueta}>
        <tbody>
          {Array.from({ length: 5 }, (_, i) => (
            <tr key={i} className={estilos.esqueleto}>
              <td colSpan={columnas}>
                <span />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Anterior / Siguiente. */
export function Paginacion({
  anterior,
  siguiente,
  ir,
  pagina,
}: {
  anterior: boolean;
  siguiente: boolean;
  ir: (pagina: number) => void;
  pagina: number;
}) {
  if (!anterior && !siguiente) return null;
  return (
    <nav className={estilos.paginacion} aria-label="Paginación">
      <button type="button" className={estilos.botonSecundario} disabled={!anterior} onClick={() => ir(pagina - 1)}>
        Anterior
      </button>
      <button type="button" className={estilos.botonSecundario} disabled={!siguiente} onClick={() => ir(pagina + 1)}>
        Siguiente
      </button>
    </nav>
  );
}
