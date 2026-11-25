export const MAXIMO_BYTES = 2 * 1024 * 1024;
export const TIPOS = ['image/png', 'image/jpeg', 'image/webp'];

/** CC-27: los mismos límites que valida el servidor, para avisar antes de subir (el ancho y el contenido los revisa él). */
export function revisarArchivo(archivo: File): string | null {
  if (!TIPOS.includes(archivo.type)) return 'El logo debe ser una imagen PNG, JPG o WebP.';
  if (archivo.size > MAXIMO_BYTES) return 'El logo pesa más de 2 MB.';
  return null;
}
