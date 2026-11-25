/** Dirección del servidor, sin barra final. Vacía en desarrollo (mismo origen); la APK la fija al compilar. */
export const API_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');
