import { useSyncExternalStore } from 'react';
import { temaApp } from './instancia';

/** El tema guardado de la empresa (o `null` antes del primer ingreso en este celular). */
export function useTema() {
  return useSyncExternalStore(temaApp.suscribir, temaApp.leer);
}
