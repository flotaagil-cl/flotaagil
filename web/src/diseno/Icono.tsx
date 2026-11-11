import { ICONOS, type NombreIcono } from './iconos';

interface Props {
  nombre: NombreIcono;
  tamano?: number;
  className?: string;
}

/** Ícono decorativo: el texto que lo acompaña da el significado, así que queda oculto a los lectores. */
export function Icono({ nombre, tamano = 20, className }: Props) {
  return (
    <svg
      className={className}
      width={tamano}
      height={tamano}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={ICONOS[nombre]} />
    </svg>
  );
}
