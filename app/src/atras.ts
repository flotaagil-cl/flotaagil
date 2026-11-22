/**
 * Botón o gesto «Atrás» de Android. Cada pantalla secundaria registra qué hace «Volver» (la misma lógica de su botón
 * en pantalla); `App` escucha `backButton` y ejecuta la del tope de la pila. Si no hay ninguna (el inicio u otra
 * pantalla sin «Volver»), la app se minimiza.
 */

import { useEffect, useRef } from 'react';

type Manejador = () => void;

const pila: Manejador[] = [];

export function registrarAtras(manejador: Manejador): () => void {
  pila.push(manejador);
  return () => {
    const posicion = pila.lastIndexOf(manejador);
    if (posicion >= 0) pila.splice(posicion, 1);
  };
}

/** Ejecuta el «Volver» de la pantalla abierta. Devuelve false si no hay ninguno. */
export function manejarAtras(): boolean {
  const manejador = pila.at(-1);
  if (!manejador) return false;
  manejador();
  return true;
}

/** Registra el «Volver» de la pantalla mientras esté montada. Solo las pantallas hoja lo usan (una a la vez). */
export function useAtras(manejador: Manejador): void {
  const ultimo = useRef(manejador);
  useEffect(() => {
    ultimo.current = manejador;
  });
  useEffect(() => registrarAtras(() => ultimo.current()), []);
}
