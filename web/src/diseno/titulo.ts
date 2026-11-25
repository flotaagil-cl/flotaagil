import { useEffect } from 'react';

export const MARCA_DEFECTO = 'FlotaÁgil';

/** Formatea el título de la pestaña del navegador como «Página · Marca». */
export function formatearTitulo(pagina: string, marca?: string | null): string {
  const texto = pagina.trim();
  const sufijo = marca?.trim() || MARCA_DEFECTO;
  if (!texto) return sufijo;
  return `${texto} · ${sufijo}`;
}

/** Actualiza `document.title` con el formato «Página · Marca». */
export function useTitulo(pagina: string, marca?: string | null): void {
  useEffect(() => {
    document.title = formatearTitulo(pagina, marca);
  }, [pagina, marca]);
}
