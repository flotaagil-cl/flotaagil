import type { ComponentProps } from 'react';
import { claseBoton, type VarianteBoton } from './clases';

interface Props extends ComponentProps<'button'> {
  variante?: VarianteBoton;
  /** Ocupa todo el ancho (formularios del portal). */
  ancho?: boolean;
  /** Mientras se envía: queda deshabilitado y lo anuncia. */
  cargando?: boolean;
}

export function Boton({ variante = 'principal', ancho = false, cargando = false, type = 'button', className, disabled, ...resto }: Props) {
  return (
    <button
      type={type}
      className={[claseBoton(variante, ancho), className].filter(Boolean).join(' ')}
      disabled={disabled || cargando}
      aria-busy={cargando || undefined}
      {...resto}
    />
  );
}
