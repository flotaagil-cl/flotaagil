/**
 * Trazos de los íconos del portal (cuadro de 24 × 24, línea de 2 px, color del texto). Los usan <Icono> y el
 * mapa de respaldo.
 */
export const ICONOS = {
  avion: 'M21 12c0-.8-.7-1.5-1.5-1.5H15L10 3H8l2.5 7.5H6L4.5 8.5H3l1 3.5-1 3.5h1.5L6 13.5h4.5L8 21h2l5-7.5h4.5c.8 0 1.5-.7 1.5-1.5Z',
  despegue: 'M3 20h18M4 14.5l5.5.5 6.5-6 2.5-.8a1.6 1.6 0 0 1 1 3L13 15l-3 4.5-1.5-.2 1.2-3.8-4.4-.4-1.8 1.4L3 16l1-1.5Z',
  aterrizaje: 'M3 20h18M3 7.5l1-.5 1.5 1.2 4.2 1.2-.4-4 1.4-.6 3 4.8 6.2 1.8a1.6 1.6 0 0 1-.9 3.1L4.5 11 3 7.5Z',
  auto: 'M5 16v-4.5L7 7h10l2 4.5V16H5Zm0 0v2.5h3V16m8 0v2.5h3V16M7.5 13h.01M16.5 13h.01',
  candado: 'M6 11h12v9H6v-9Zm2.5 0V8a3.5 3.5 0 0 1 7 0v3',
  destino: 'M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21Zm0-9.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z',
  derecha: 'm9 6 6 6-6 6',
  atras: 'm15 6-6 6 6 6',
  mensaje: 'M4 5h16v11H9l-5 4V5Z',
  check: 'm5 12.5 4.5 4.5L19 7.5',
  cerrar: 'M6 6l12 12M18 6 6 18',
  mas: 'M12 5v14M5 12h14',
  menos: 'M5 12h14',
  usuario: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0',
  salir: 'M15 4h4v16h-4M10 8l-4 4 4 4M6 12h10',
  basurero: 'M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13M10 11v6M14 11v6',
  reloj: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-13v4.5l3 2',
  lista: 'M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01',
  llave: 'M7.5 20a3.5 3.5 0 1 1 3.2-4.9L19 6.8M15.5 10.3l2 2M13.5 12.3l1.5 1.5',
} as const;

export type NombreIcono = keyof typeof ICONOS;
