import type { ReactNode } from 'react';
import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import { mensajeDeError } from '../errores';

/** Celda con su título: en celular la tabla pasa a tarjetas y el título va a la izquierda (CSS). */
export function Celda({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <td data-titulo={titulo}>
      <div>{children}</div>
    </td>
  );
}

/** Error de una consulta con «Reintentar». */
export function FallaDeCarga({ error, que, reintentar }: { error: unknown; que: string; reintentar: () => void }) {
  return (
    <div className={estilos.vacio} role="alert">
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
      <h1>No encontrado</h1>
      <p>No existe {que} o no es de tu empresa.</p>
      <Link to={volverA}>{texto}</Link>
    </section>
  );
}

/** Filas de espera de una tabla mientras llega la primera página. */
export function Esqueleto({ etiqueta, columnas }: { etiqueta: string; columnas: number }) {
  return (
    <table className={estilos.tabla} aria-busy="true" aria-label={etiqueta}>
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
