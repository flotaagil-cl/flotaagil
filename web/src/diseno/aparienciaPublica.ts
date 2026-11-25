/**
 * CC-27 (HU-79): paleta y logo de la empresa en las páginas públicas del portal, sin parpadeo de los colores
 * predeterminados. Lo guardado en el navegador se aplica de inmediato y se actualiza con el servidor; en la primera
 * visita la pantalla espera la respuesta (o su falla, o un plazo corto) antes de pintar. No carga nada de la sesión.
 */

import { useEffect, useState } from 'react';
import type { components } from '../api/esquema';
import type { Almacen } from '../entorno';
import { useEntorno } from '../entornoContexto';

export type Apariencia = components['schemas']['Apariencia'];

export const ESPERA_MAXIMA_MS = 2500;
const PREFIJO = 'flotaagil.apariencia.';

export function leerGuardada(almacen: Almacen | null, slug: string): Apariencia | null {
  try {
    const texto = almacen?.getItem(PREFIJO + slug);
    const datos = texto ? (JSON.parse(texto) as Apariencia) : null;
    return datos && typeof datos.paleta === 'string' ? datos : null;
  } catch {
    return null;
  }
}

export function guardar(almacen: Almacen | null, slug: string, apariencia: Apariencia): void {
  try {
    almacen?.setItem(PREFIJO + slug, JSON.stringify(apariencia));
  } catch {
    // Sin almacenamiento: la próxima visita vuelve a esperar la respuesta.
  }
}

/** `slug` null: sin empresa (marca de FlotaÁgil), listo de inmediato. */
export function useAparienciaPublica(slug: string | null): { apariencia: Apariencia | null; lista: boolean } {
  const entorno = useEntorno();
  const [estado, setEstado] = useState<{ slug: string | null; apariencia: Apariencia | null; lista: boolean }>(() => inicial(entorno.almacen, slug));
  // Otro portal en la misma pestaña: se parte de lo guardado de ese.
  const actual = estado.slug === slug ? estado : inicial(entorno.almacen, slug);

  useEffect(() => {
    if (!slug) return;
    let vigente = true;
    const plazo = window.setTimeout(() => {
      if (vigente) setEstado((e) => (e.slug === slug && e.lista ? e : { ...inicial(entorno.almacen, slug), lista: true }));
    }, ESPERA_MAXIMA_MS);
    entorno
      .fetch(new Request(`${entorno.origen}/api/publico/apariencia/${encodeURIComponent(slug)}/`))
      .then(async (respuesta) => {
        const datos = respuesta.ok ? ((await respuesta.json()) as Apariencia) : null;
        const valida = datos && typeof datos.paleta === 'string' ? datos : null;
        if (valida) guardar(entorno.almacen, slug, valida);
        if (vigente) setEstado({ slug, apariencia: valida ?? leerGuardada(entorno.almacen, slug), lista: true });
      })
      .catch(() => {
        if (vigente) setEstado({ slug, apariencia: leerGuardada(entorno.almacen, slug), lista: true });
      });
    return () => {
      vigente = false;
      window.clearTimeout(plazo);
    };
  }, [entorno, slug]);

  return { apariencia: actual.apariencia, lista: actual.lista };
}

function inicial(almacen: Almacen | null, slug: string | null) {
  const guardada = slug ? leerGuardada(almacen, slug) : null;
  return { slug, apariencia: guardada, lista: !slug || guardada !== null };
}
