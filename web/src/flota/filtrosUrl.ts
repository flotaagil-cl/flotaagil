import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router';

const ESPERA_BUSQUEDA_MS = 300;

type Cambios<C extends string> = Partial<Record<C | 'q' | 'page', string>>;

/**
 * Filtros simples guardados en la URL (`?q=…&activo=…&page=…`). La búsqueda se escribe en la URL 300 ms
 * después de dejar de teclear; cualquier cambio de filtro vuelve a la página 1.
 */
export function useFiltrosUrl<C extends string>(campos: readonly C[]) {
  const [parametros, setParametros] = useSearchParams();
  const valores = Object.fromEntries(campos.map((c) => [c, parametros.get(c) ?? ''])) as Record<C, string>;
  const q = parametros.get('q') ?? '';
  const pagina = Math.max(1, Number(parametros.get('page')) || 1);
  const [busqueda, setBusqueda] = useState(q);
  // Si la URL cambia por fuera (atrás, «Quitar filtros»), el cuadro de búsqueda la sigue.
  const [busquedaEnUrl, setBusquedaEnUrl] = useState(q);
  if (q !== busquedaEnUrl) {
    setBusquedaEnUrl(q);
    setBusqueda(q);
  }

  const cambiar = useCallback(
    (cambios: Cambios<C>, reemplazar = false) => {
      setParametros(
        (actuales) => {
          const nuevos = new URLSearchParams(actuales);
          for (const [clave, valor] of Object.entries(cambios) as [string, string][]) {
            if (valor) nuevos.set(clave, valor);
            else nuevos.delete(clave);
          }
          if (!('page' in cambios)) nuevos.delete('page');
          return nuevos;
        },
        { replace: reemplazar },
      );
    },
    [setParametros],
  );

  useEffect(() => {
    if (busqueda.trim() === q.trim()) return;
    const espera = setTimeout(() => cambiar({ q: busqueda.trim() } as Cambios<C>, true), ESPERA_BUSQUEDA_MS);
    return () => clearTimeout(espera);
  }, [busqueda, q, cambiar]);

  return { valores, q, pagina, busqueda, setBusqueda, cambiar };
}
