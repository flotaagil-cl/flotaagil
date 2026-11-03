/**
 * Tabla única de rutas. De aquí salen el router, la guarda por rol, el menú y la validación de `volver`.
 *
 * La guarda por rol es solo UX: la seguridad la pone el backend (401/403 y aislamiento por empresa).
 *
 * Todo se carga con `lazy`: el paquete inicial lleva solo el router y los contextos. La sesión, el marco del
 * panel y cada pantalla llegan en su chunk. El `handle` (título, menú, roles) queda aquí, estático, para que
 * el menú y la guarda no carguen código de las pantallas. scripts/verificar-carga.mjs comprueba al final del
 * build que el paquete inicial y el portal no cargan nada del panel ni de la sesión, y el login nada de
 * reservas ni del portal.
 */

import type { RouteObject } from 'react-router';
import type { Rol } from '../api/auth';
import { Cargando } from '../componentes/Cargando';
import { ErrorDeRuta } from '../componentes/ErrorDeRuta';

export interface Manejo {
  titulo: string;
  /** Aparece en el menú. */
  menu?: boolean;
  /** Roles que pueden verla; sin roles, cualquiera con sesión del panel. */
  roles?: Rol[];
}

export const ROLES_PANEL: Rol[] = ['ADMINISTRADOR', 'DESPACHADOR'];
/** Administración de flota (HU-10): solo el administrador. */
export const ROLES_ADMIN: Rol[] = ['ADMINISTRADOR'];

/** Pantallas del panel (con sesión). Las nuevas se agregan aquí. */
export const pantallasDelPanel: RouteObject[] = [
  {
    index: true,
    lazy: async () => ({ Component: (await import('../paginas/Inicio')).Inicio }),
    handle: { titulo: 'Inicio', menu: true, roles: ROLES_PANEL } satisfies Manejo,
  },
  {
    path: 'reservas',
    handle: { titulo: 'Reservas', menu: true, roles: ROLES_PANEL } satisfies Manejo,
    children: [
      { index: true, lazy: async () => ({ Component: (await import('../reservas/paginas/Listado')).Listado }) },
      {
        path: 'nueva',
        lazy: async () => ({ Component: (await import('../reservas/paginas/Nueva')).Nueva }),
        handle: { titulo: 'Nueva reserva', roles: ROLES_PANEL } satisfies Manejo,
      },
      {
        path: ':id',
        lazy: async () => ({ Component: (await import('../reservas/paginas/Detalle')).Detalle }),
        handle: { titulo: 'Reserva', roles: ROLES_PANEL } satisfies Manejo,
      },
      {
        path: ':id/editar',
        lazy: async () => ({ Component: (await import('../reservas/paginas/Editar')).Editar }),
        handle: { titulo: 'Editar reserva', roles: ROLES_PANEL } satisfies Manejo,
      },
    ],
  },
  {
    path: 'mapa',
    lazy: async () => ({ Component: (await import('../mapa/Mapa')).Mapa }),
    handle: { titulo: 'Mapa', menu: true, roles: ROLES_PANEL } satisfies Manejo,
  },
  {
    path: 'vehiculos',
    handle: { titulo: 'Vehículos', menu: true, roles: ROLES_ADMIN } satisfies Manejo,
    children: [
      { index: true, lazy: async () => ({ Component: (await import('../flota/paginas/Vehiculos')).Vehiculos }) },
      {
        path: 'nuevo',
        lazy: async () => ({ Component: (await import('../flota/paginas/VehiculoNuevo')).VehiculoNuevo }),
        handle: { titulo: 'Nuevo vehículo', roles: ROLES_ADMIN } satisfies Manejo,
      },
      {
        path: 'importar',
        lazy: async () => ({ Component: (await import('../flota/paginas/ImportarVehiculos')).ImportarVehiculos }),
        handle: { titulo: 'Cargar vehículos por CSV', roles: ROLES_ADMIN } satisfies Manejo,
      },
      {
        path: ':id',
        lazy: async () => ({ Component: (await import('../flota/paginas/Vehiculo')).Vehiculo }),
        handle: { titulo: 'Vehículo', roles: ROLES_ADMIN } satisfies Manejo,
      },
    ],
  },
  {
    path: 'conductores',
    handle: { titulo: 'Conductores', menu: true, roles: ROLES_ADMIN } satisfies Manejo,
    children: [
      { index: true, lazy: async () => ({ Component: (await import('../flota/paginas/Conductores')).Conductores }) },
      {
        path: 'nuevo',
        lazy: async () => ({ Component: (await import('../flota/paginas/ConductorNuevo')).ConductorNuevo }),
        handle: { titulo: 'Nuevo conductor', roles: ROLES_ADMIN } satisfies Manejo,
      },
      {
        path: 'importar',
        lazy: async () => ({ Component: (await import('../flota/paginas/ImportarConductores')).ImportarConductores }),
        handle: { titulo: 'Cargar conductores por CSV', roles: ROLES_ADMIN } satisfies Manejo,
      },
      {
        path: ':id',
        lazy: async () => ({ Component: (await import('../flota/paginas/Conductor')).Conductor }),
        handle: { titulo: 'Conductor', roles: ROLES_ADMIN } satisfies Manejo,
      },
    ],
  },
];

export function crearRutas(pantallas: RouteObject[] = pantallasDelPanel): RouteObject[] {
  const comunes = { hydrateFallbackElement: <Cargando />, errorElement: <ErrorDeRuta /> };
  return [
    {
      // Raíz de sesión (lazy): /login y el panel. El portal y la página no encontrada quedan fuera.
      lazy: async () => ({ Component: (await import('../sesion/RaizSesion')).RaizSesion }),
      ...comunes,
      children: [
        { path: '/login', lazy: async () => ({ Component: (await import('../paginas/Login')).Login }) },
        {
          lazy: async () => ({ Component: (await import('./RutaAutenticada')).RutaAutenticada }),
          children: [
            {
              path: '/',
              lazy: async () => ({ Component: (await import('../componentes/Layout')).Layout }),
              children: pantallas,
            },
          ],
        },
      ],
    },
    {
      // Portal público del pasajero (HU-19): sin sesión ni refresh silencioso.
      path: '/solicitar/:slug',
      lazy: async () => ({ Component: (await import('../portal/LayoutPortal')).LayoutPortal }),
      ...comunes,
      children: [
        { index: true, lazy: async () => ({ Component: (await import('../portal/paginas/Solicitar')).Solicitar }) },
        {
          path: 'privacidad',
          lazy: async () => ({ Component: (await import('../portal/paginas/Privacidad')).Privacidad }),
        },
      ],
    },
    {
      path: '*',
      lazy: async () => ({ Component: (await import('../paginas/NoEncontrada')).NoEncontrada }),
      ...comunes,
    },
  ];
}

export interface EntradaMenu {
  ruta: string;
  titulo: string;
}

/** Menú generado desde la tabla, filtrado por rol: solo muestra pantallas que existen. */
export function entradasDeMenu(rutas: RouteObject[], rol: Rol, base = ''): EntradaMenu[] {
  return rutas.flatMap((ruta) => {
    const camino = ruta.path ? `${base.replace(/\/$/, '')}/${ruta.path.replace(/^\//, '')}` : base || '/';
    const manejo = ruta.handle as Manejo | undefined;
    const propia =
      manejo?.menu && (!manejo.roles || manejo.roles.includes(rol)) ? [{ ruta: camino, titulo: manejo.titulo }] : [];
    return [...propia, ...entradasDeMenu(ruta.children ?? [], rol, camino)];
  });
}
