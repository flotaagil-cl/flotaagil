// Generado por scripts/generar-paletas.mjs desde backend/apps/cuentas/paletas.json. No editar a mano.
export const PALETA_PREDETERMINADA = 'tiffany';

export const PALETAS = [
  { clave: 'tiffany', nombre: 'Tiffany' },
  { clave: 'oceano', nombre: 'Océano' },
  { clave: 'cobalto', nombre: 'Cobalto' },
  { clave: 'indigo', nombre: 'Índigo' },
  { clave: 'violeta', nombre: 'Violeta' },
  { clave: 'orquidea', nombre: 'Orquídea' },
  { clave: 'magenta', nombre: 'Magenta' },
  { clave: 'pizarra', nombre: 'Pizarra' },
  { clave: 'grafito', nombre: 'Grafito' },
  { clave: 'cian', nombre: 'Cian' },
] as const;

export type ClavePaleta = (typeof PALETAS)[number]['clave'];
