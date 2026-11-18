import { lazy, Suspense } from 'react';
import { RouterProvider, type createBrowserRouter, type RouteObject } from 'react-router';
import type { Entorno } from './entorno';
import { EntornoContexto } from './entornoContexto';
import { RutasContexto } from './rutas/contexto';
import { ProveedorMapa } from './diseno/mapa/Mapa';
import { MapaRespaldo } from './diseno/mapa/MapaRespaldo';
import { proveedorDelEntorno } from './diseno/mapa/proveedor';
import type { PropsMapa } from './diseno/mapa/tipos';

type Router = ReturnType<typeof createBrowserRouter>;

// HU-70: el mapa de OpenStreetMap (y Leaflet) se carga aparte, solo cuando una pantalla dibuja un mapa; el paquete
// inicial no incluye nada de src/mapa (verificar-carga).
const MapaOsmPortal = lazy(() => import('./mapa/MapaOsmPortal').then((m) => ({ default: m.MapaOsmPortal })));

function MapaOsmDiferido(props: PropsMapa) {
  return (
    <Suspense fallback={<MapaRespaldo {...props} />}>
      <MapaOsmPortal {...props} />
    </Suspense>
  );
}

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
  return proveedorDelEntorno() === 'osm' ? <ProveedorMapa componente={MapaOsmDiferido}>{contenido}</ProveedorMapa> : contenido;
}
