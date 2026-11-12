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

import { Navigate, type RouteObject } from 'react-router';
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
/** HU-33: cuentas web de la empresa cliente (HU-34) y del pasajero (HU-35), con el mismo inicio de sesión. */
export const ROLES_CONVENIO: Rol[] = ['CONVENIO'];
export const ROLES_PASAJERO: Rol[] = ['PASAJERO'];

/** HU-33: adónde llega cada rol después de iniciar sesión. */
export function inicioDeRol(rol: Rol): string {
  if (rol === 'CONVENIO') return '/mi-convenio';
  // HU-39: el pasajero llega a pedir su traslado.
  if (rol === 'PASAJERO') return '/pedir';
  return '/';
}

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
        path: 'contingencia',
        lazy: async () => ({ Component: (await import('../reservas/paginas/Contingencia')).Contingencia }),
        handle: { titulo: 'Reserva de contingencia', roles: ROLES_PANEL } satisfies Manejo,
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
  {
    path: 'conversaciones',
    handle: { titulo: 'Conversaciones', menu: true, roles: ROLES_PANEL } satisfies Manejo,
    children: [
      { index: true, lazy: async () => ({ Component: (await import('../conversaciones/paginas/Conversaciones')).Conversaciones }) },
      {
        path: ':id',
        lazy: async () => ({ Component: (await import('../conversaciones/paginas/Conversacion')).Conversacion }),
        handle: { titulo: 'Conversación', roles: ROLES_PANEL } satisfies Manejo,
      },
    ],
  },
  {
    path: 'reportes',
    lazy: async () => ({ Component: (await import('../reportes/paginas/Reportes')).Reportes }),
    handle: { titulo: 'Reportes', menu: true, roles: ROLES_ADMIN } satisfies Manejo,
  },
  {
    path: 'mi-convenio',
    lazy: async () => ({ Component: (await import('../cuentas-web/MiConvenio')).MiConvenio }),
    handle: { titulo: 'Mi convenio', menu: true, roles: ROLES_CONVENIO } satisfies Manejo,
  },
  {
    path: 'usuarios',
    lazy: async () => ({ Component: (await import('../usuarios/Usuarios')).Usuarios }),
    handle: { titulo: 'Usuarios', menu: true, roles: ROLES_ADMIN } satisfies Manejo,
  },
  {
    path: 'caja',
    lazy: async () => ({ Component: (await import('../caja/Caja')).Caja }),
    handle: { titulo: 'Cierre de caja', menu: true, roles: ROLES_ADMIN } satisfies Manejo,
  },
  {
    path: 'convenios',
    handle: { titulo: 'Convenios', menu: true, roles: ROLES_ADMIN } satisfies Manejo,
    children: [
      { index: true, lazy: async () => ({ Component: (await import('../convenios/paginas/Convenios')).Convenios }) },
      {
        path: ':id',
        lazy: async () => ({ Component: (await import('../convenios/paginas/Convenio')).Convenio }),
        handle: { titulo: 'Convenio' } satisfies Manejo,
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
        // Ingreso del portal con la marca de la empresa (HU-38); necesita la sesión, por eso vive aquí.
        {
          path: '/solicitar/:slug/ingresar',
          lazy: async () => ({ Component: (await import('../paginas/IngresarPortal')).IngresarPortal }),
        },
        {
          lazy: async () => ({ Component: (await import('./RutaAutenticada')).RutaAutenticada }),
          children: [
            { path: '/primer-ingreso', lazy: async () => ({ Component: (await import('../paginas/PrimerIngreso')).PrimerIngreso }) },
            // DC-44: aceptar el aviso de privacidad una vez (cuentas antiguas o versión nueva).
            {
              path: '/aceptar-privacidad',
              lazy: async () => ({ Component: (await import('../paginas/AceptarPrivacidad')).AceptarPrivacidad }),
            },
            // HU-44: los viajes del pasajero, próximos y anteriores.
            { path: '/mis-viajes', lazy: async () => ({ Component: (await import('../viajes/MisViajes')).MisViajes }) },
            // HU-43: el viaje del pasajero con su estado, conductor y vuelo.
            { path: '/mis-viajes/:id', lazy: async () => ({ Component: (await import('../viajes/TuViaje')).TuViaje }) },
            // HU-45: datos, contraseña y eliminar la cuenta.
            { path: '/mi-perfil', lazy: async () => ({ Component: (await import('../perfil/MiPerfil')).MiPerfil }) },
            // La pantalla «Mis reservas» de HU-35 era una lista de viajes: la reemplaza «Mis viajes» (HU-44).
            { path: '/mis-reservas', element: <Navigate to="/mis-viajes" replace /> },
            // HU-39: inicio y pedido del pasajero con el marco del portal (fuera del marco del panel).
            { path: '/pedir/:tipo?', lazy: async () => ({ Component: (await import('../pedido/Pedir')).Pedir }) },
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
      // Portal público de la empresa (HU-19): sin sesión ni refresh silencioso.
      path: '/solicitar/:slug',
      lazy: async () => ({ Component: (await import('../portal/LayoutPortal')).LayoutPortal }),
      ...comunes,
      children: [
        // HU-40 (CC-18): sin pedido como invitado; la dirección del portal lleva al ingreso de la empresa.
        { index: true, lazy: async () => ({ Component: (await import('../portal/paginas/IrAlIngreso')).IrAlIngreso }) },
        {
          path: 'privacidad',
          lazy: async () => ({ Component: (await import('../portal/paginas/Privacidad')).Privacidad }),
        },
        {
          path: 'registro-empresa',
          lazy: async () => ({ Component: (await import('../portal/paginas/RegistroEmpresa')).RegistroEmpresa }),
        },
        {
          path: 'cuenta',
          lazy: async () => ({ Component: (await import('../portal/paginas/CrearCuenta')).CrearCuenta }),
          // HU-38: en el celular el título va en la banda con el degradé, sin la barra.
          handle: { barraMovil: 'oculta', completa: true },
        },
        {
          // HU-41: volver a activar la cuenta (reenviar el mensaje o corregir el número).
          path: 'activar',
          lazy: async () => ({ Component: (await import('../portal/paginas/Activar')).Activar }),
          handle: { barraMovil: 'oculta', completa: true },
        },
      ],
    },
    {
      // HU-35: recuperar la contraseña por correo. Pública, sin la sesión del panel.
      path: '/recuperar',
      lazy: async () => ({ Component: (await import('../cuentas-web/Recuperar')).Recuperar }),
      ...comunes,
    },
    {
      path: '/recuperar/:uid/:token',
      lazy: async () => ({ Component: (await import('../cuentas-web/Recuperar')).ElegirPassword }),
      ...comunes,
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
