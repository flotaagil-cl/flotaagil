import type { ReactNode } from 'react';
import c from './direcciones.module.css';

/** HU-71: contenedor relativo para que la lista de sugerencias quede justo bajo el campo. */
export function ConSugerencias({ children, lista }: { children: ReactNode; lista: ReactNode }) {
  return (
    <div className={c.envoltura}>
      {children}
      {lista}
    </div>
  );
}
