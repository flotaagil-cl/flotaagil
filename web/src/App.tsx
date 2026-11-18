import { RouterProvider, type createBrowserRouter, type RouteObject } from 'react-router';
import type { Entorno } from './entorno';
import { EntornoContexto } from './entornoContexto';
import { RutasContexto } from './rutas/contexto';
import { ProveedorMapa } from './diseno/mapa/Mapa';
import { MapaOsmPortal } from './mapa/MapaOsmPortal';
import { proveedorDelEntorno } from './mapa/proveedor';

type Router = ReturnType<typeof createBrowserRouter>;

/**
 * Raíz de la aplicación. La sesión no está aquí: la monta la raíz de sesión (lazy) solo en /login y en el
 * panel, así el portal público (/solicitar) no la carga ni hace el refresh silencioso.
 */
export function App({ entorno, rutas, router }: { entorno: Entorno; rutas: RouteObject[]; router: Router }) {
  const contenido = (
    <EntornoContexto.Provider value={entorno}>
      <RutasContexto.Provider value={rutas}>
        <RouterProvider router={router} />
      </RutasContexto.Provider>
    </EntornoContexto.Provider>
  );
  // HU-70: con OpenStreetMap, los mapas del portal (diseno/mapa) son reales; si no, el de respaldo.
  return proveedorDelEntorno() === 'osm' ? <ProveedorMapa componente={MapaOsmPortal}>{contenido}</ProveedorMapa> : contenido;
}
