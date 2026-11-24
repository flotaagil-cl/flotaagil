/**
 * Trazos vectoriales reutilizables de la app del conductor (cuadro 24 × 24, línea de 2 px).
 * Alineados con `web/src/diseno/iconos.ts` para mantener la identidad visual de FlotaÁgil.
 */
const ICONOS = {
  auto: 'M5 16v-4.5L7 7h10l2 4.5V16H5Zm0 0v2.5h3V16m8 0v2.5h3V16M7.5 13h.01M16.5 13h.01',
  correo: 'M4 6h16v12H4V6Zm0 0 8 6 8-6',
  candado: 'M6 11h12v9H6v-9Zm2.5 0V8a3.5 3.5 0 0 1 7 0v3',
  ojo: 'M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12Zm10 3a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  ojoCerrado:
    'M3 3l18 18M10.6 10.6a3 3 0 0 0 4.2 4.2M9.9 5.1A10.4 10.4 0 0 1 12 5c6.4 0 10 7 10 7a18.2 18.2 0 0 1-3.3 4.3M6.6 6.6A18.3 18.3 0 0 0 2 12s3.6 7 10 7c1.6 0 3.1-.4 4.4-1',
  llave: 'M7.5 20a3.5 3.5 0 1 1 3.2-4.9L19 6.8M15.5 10.3l2 2M13.5 12.3l1.5 1.5',
  alerta: 'M12 3 2.5 20h19L12 3Zm0 7v4m0 3.5h.01',
} as const;

export type NombreIcono = keyof typeof ICONOS;

interface Props {
  nombre: NombreIcono;
  tamano?: number;
  className?: string;
}

/** Ícono decorativo en SVG; los textos o etiquetas aria proveen el significado accesible. */
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
