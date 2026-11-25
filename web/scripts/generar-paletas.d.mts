export function mezclar(color: string, fondo: string, peso: number): string;
export function tokensDe(paleta: { oscuro: string; medio: string; claro: string }): Record<string, string>;
export function generar(
  catalogo: { predeterminada: string; paletas: { clave: string; nombre: string; oscuro: string; medio: string; claro: string }[] },
  tokensCss: string,
): { css: string; ts: string };
