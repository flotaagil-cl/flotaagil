import { createContext } from 'react';
import { MapaRespaldo } from './MapaRespaldo';
import type { ComponenteMapa } from './tipos';

/** Mapa que usan las pantallas del portal. Sin proveedor, el de respaldo. */
export const ContextoMapa = createContext<ComponenteMapa>(MapaRespaldo);
