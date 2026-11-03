/**
 * Alerta de viaje asignado (HU-14): sonora, vibración y, con la app en segundo plano, notificación del sistema.
 *
 * - Sonido: tres pitidos generados con Web Audio (no hace falta un archivo de audio).
 * - Vibración: patrón corto (navigator.vibrate, si el WebView lo permite).
 * - Notificación: @capacitor/local-notifications 7.0.7, con sonido del sistema; al tocarla se abre la app.
 */

import { LocalNotifications } from '@capacitor/local-notifications';
import type { Asignacion } from './canal';

const PATRON_VIBRACION = [400, 200, 400, 200, 400];

let contexto: AudioContext | null = null;

function pitidos() {
  try {
    contexto ??= new AudioContext();
    const inicio = contexto.currentTime;
    for (let i = 0; i < 3; i += 1) {
      const oscilador = contexto.createOscillator();
      const volumen = contexto.createGain();
      oscilador.frequency.value = 880;
      volumen.gain.setValueAtTime(0.4, inicio + i * 0.45);
      volumen.gain.exponentialRampToValueAtTime(0.001, inicio + i * 0.45 + 0.35);
      oscilador.connect(volumen).connect(contexto.destination);
      oscilador.start(inicio + i * 0.45);
      oscilador.stop(inicio + i * 0.45 + 0.36);
    }
  } catch {
    // Sin audio disponible: quedan la vibración y la notificación.
  }
}

export function textoDeLaNotificacion(asignacion: Asignacion): { titulo: string; cuerpo: string } {
  const vuelo = asignacion.vuelo ? ` · vuelo ${asignacion.vuelo.numero}` : '';
  return {
    titulo: 'Nuevo viaje asignado',
    cuerpo: `${asignacion.origen.direccion} → ${asignacion.destino.direccion}${vuelo}. Tienes 60 s para responder.`,
  };
}

/** Avisa con sonido y vibración; si la app no está a la vista, además con una notificación del sistema. */
export async function alertar(asignacion: Asignacion, enSegundoPlano: boolean): Promise<void> {
  pitidos();
  try {
    navigator.vibrate?.(PATRON_VIBRACION);
  } catch {
    // El WebView puede no permitirlo.
  }
  if (!enSegundoPlano) return;
  try {
    const { titulo, cuerpo } = textoDeLaNotificacion(asignacion);
    await LocalNotifications.schedule({
      notifications: [{ id: asignacion.asignacion % 2_000_000_000, title: titulo, body: cuerpo, extra: { viaje: asignacion.viaje } }],
    });
  } catch {
    // Sin permiso de notificaciones: el aviso queda en la app.
  }
}

export async function pedirPermisoDeNotificaciones(): Promise<void> {
  try {
    const { display } = await LocalNotifications.checkPermissions();
    if (display !== 'granted') await LocalNotifications.requestPermissions();
  } catch {
    // En el navegador no aplica.
  }
}
