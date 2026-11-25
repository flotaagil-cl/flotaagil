import type { ReactNode } from 'react';
import type { components } from '../api/esquema';
import estilos from './LogoEmpresa.module.css';

export type Apariencia = components['schemas']['Apariencia'];

interface Props {
  apariencia: Apariencia | null | undefined;
  variante: 'panel' | 'portal';
  /** Nombre visible de la empresa, para el texto alternativo. */
  empresa: string;
  /** Lo que se muestra sin logo ni iniciales: la marca de FlotaÁgil. */
  respaldo: ReactNode;
  className?: string;
}

/**
 * CC-27: el logo de la empresa sobre una base blanca redondeada (un JPG con fondo blanco no se ve como un cuadro).
 * CC-21 (DC-86): sin logo, las iniciales y, si no hay, el respaldo.
 */
export function LogoEmpresa({ apariencia, variante, empresa, respaldo, className }: Props) {
  const ruta = apariencia?.logo?.[variante];
  if (!ruta) {
    if (!apariencia?.iniciales) return <>{respaldo}</>;
    return (
      <span className={`${estilos.base} ${estilos.iniciales} ${estilos[variante]}${className ? ` ${className}` : ''}`} role="img" aria-label={`Iniciales de ${empresa}`}>
        {apariencia.iniciales}
      </span>
    );
  }
  return (
    <span className={`${estilos.base}${className ? ` ${className}` : ''}`}>
      <img className={estilos[variante]} src={ruta} alt={`Logo de ${empresa}`} />
    </span>
  );
}
