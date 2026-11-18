/**
 * Avisos del chat y de llegada en el panel (HU-63). El sonido es el de las alertas de vuelo (HU-28). Si la pestaña no
 * está a la vista y el navegador lo permite, además una notificación del sistema (Notification API). Sin permiso, el
 * aviso queda en la pantalla.
 */

export { sonarAlerta as sonar } from '../alertas/sonido';

export function avisosDisponibles(): boolean {
  return typeof window !== 'undefined' && 'Notification' in window;
}

/** Notificación del sistema solo con la pestaña oculta y el permiso dado. */
export function notificar(titulo: string, cuerpo: string): void {
  if (!avisosDisponibles() || Notification.permission !== 'granted' || !document.hidden) return;
  try {
    new Notification(titulo, { body: cuerpo, tag: 'flotaagil-chat' });
  } catch {
    // Algunos navegadores solo permiten notificaciones desde un service worker.
  }
}
