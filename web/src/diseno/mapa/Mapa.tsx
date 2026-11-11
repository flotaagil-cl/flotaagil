import { createElement, useContext, type ReactNode } from 'react';
import { ContextoMapa } from './contexto';
import type { ComponenteMapa, PropsMapa } from './tipos';

/**
 * Adaptador del mapa: las pantallas usan <Mapa> y el proveedor decide cuál se dibuja. Para pasar al mapa real
 * basta con envolver el portal en <ProveedorMapa componente={MapaReal}>, sin tocar las pantallas.
 */
export function Mapa(props: PropsMapa) {
  return createElement(useContext(ContextoMapa), props);
}

export function ProveedorMapa({ componente, children }: { componente: ComponenteMapa; children: ReactNode }) {
  return <ContextoMapa.Provider value={componente}>{children}</ContextoMapa.Provider>;
}
