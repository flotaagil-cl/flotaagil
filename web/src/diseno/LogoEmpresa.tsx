import type { ReactNode } from 'react';
import type { components } from '../api/esquema';
import estilos from './LogoEmpresa.module.css';

export type Apariencia = components['schemas']['Apariencia'];

interface Props {
  apariencia: Apariencia | null | undefined;
  variante: 'panel' | 'portal';
  /** Razón social, para el texto alternativo. */
  empresa: string;
  /** Lo que se muestra sin logo propio: la marca de FlotaÁgil. */
  respaldo: ReactNode;
  className?: string;
}

/** CC-27: el logo de la empresa sobre una base blanca redondeada (un JPG con fondo blanco no se ve como un cuadro). */
export function LogoEmpresa({ apariencia, variante, empresa, respaldo, className }: Props) {
  const ruta = apariencia?.logo?.[variante];
  if (!ruta) return <>{respaldo}</>;
  return (
    <span className={`${estilos.base}${className ? ` ${className}` : ''}`}>
      <img className={estilos[variante]} src={ruta} alt={`Logo de ${empresa}`} />
    </span>
  );
}
