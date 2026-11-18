/** HU-65 (DC-62): utilidades de Web Push del portal. */

export function pushDisponible(): boolean {
  return typeof window !== 'undefined' && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
}

/** La clave VAPID en base64url, como la espera `pushManager.subscribe`. */
export function claveComoBytes(clave: string): Uint8Array<ArrayBuffer> {
  const base64 = (clave + '='.repeat((4 - (clave.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/');
  const binario = atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(binario.length));
  for (let i = 0; i < binario.length; i += 1) bytes[i] = binario.charCodeAt(i);
  return bytes;
}
