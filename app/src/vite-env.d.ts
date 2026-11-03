/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** URL del backend, p. ej. http://10.0.2.2:8000 en el emulador o https://api.flotaagil.cl. */
  readonly VITE_API_URL?: string;
}
