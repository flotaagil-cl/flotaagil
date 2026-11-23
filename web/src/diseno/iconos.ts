/**
 * Trazos de los íconos del portal y del panel (cuadro de 24 × 24, línea de 2 px, color del texto).
 * Los usan <Icono> y el mapa de respaldo.
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
  abajo: 'm6 9 6 6 6-6',
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
  inicio: 'M3 10.5 12 3l9 7.5M5 9.5V20h5v-6h4v6h5V9.5',
  mapa: 'M3 6.5 9 4l6 2.5L21 4v13.5L15 20l-6-2.5L3 20V6.5ZM9 4v13.5M15 6.5V20',
  calendario: 'M4 7h16v13H4V7Zm0 4h16M8 4v3M16 4v3',
  historial: 'M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5M12 7v5l3 2',
  volante: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-7a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm-8.5-2h6.5m4 0h6.5M12 14v7',
  convenios: 'M3 20h18M5 20V6l7-3 7 3v14M9 10h2M13 10h2M9 14h2M13 14h2',
  caja: 'M3 7h18v10H3V7Zm9 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4ZM7 12h.01M17 12h.01',
  reportes: 'M4 20h16M7 16v-5M12 16V8M17 16v-3',
  usuarios: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm14 10v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75',
  configuracion: 'M4 6h16M4 12h16M4 18h16M9 4v4M15 10v4M11 16v4',
  alerta: 'M12 3 2.5 20h19L12 3Zm0 7v4m0 3.5h.01',
  flechaDerecha: 'M5 12h14m-5-5 5 5-5 5',
  enlace: 'M10 13a5 5 0 0 0 7.07 0l2.83-2.83a5 5 0 0 0-7.07-7.07L11 4.93M14 11a5 5 0 0 0-7.07 0l-2.83 2.83a5 5 0 0 0 7.07 7.07L13 19.07',
} as const;

export type NombreIcono = keyof typeof ICONOS;
