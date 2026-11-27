/** Etiquetas y helpers compartidos entre las vistas del chat del panel. */

const ROLES: Record<string, string> = {
  ADMINISTRADOR: 'Administrador',
  DESPACHADOR: 'Despachador',
  CONDUCTOR: 'Conductor',
};

export function etiquetaRol(rol: string): string {
  return ROLES[rol] ?? rol;
}

export function normalizarBusqueda(valor: string): string {
  return valor
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
    .toLowerCase();
}
