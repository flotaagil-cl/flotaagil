/**
 * Llamadas del portal público: /api/portal/{slug}/ (HU-19), crear cuenta y registro de empresa. Desde HU-40
 * (CC-18) no hay pedido sin cuenta.
 *
 * Sin sesión: cliente openapi-fetch propio, sin el middleware de access y renovación del panel. Las rutas
 * del portal no cargan nada de src/sesion/ (lo verifica scripts/verificar-carga.mjs).
 */

import { useMutation, useQuery } from '@tanstack/react-query';
import createClient, { type Client } from 'openapi-fetch';
import type { Entorno } from '../entorno';
import type { components, paths } from '../api/esquema';
import { resultado } from '../api/resultado';

export type EmpresaPublica = components['schemas']['EmpresaPublica'];
export type SolicitudConvenio = components['schemas']['SolicitudConvenioRequest'];
/** Datos del viaje que envía el formulario (los mismos del convenio, sin su declaración). */
export type Solicitud = Omit<SolicitudConvenio, 'declara_autorizacion'>;
/** El formulario sirve a los dos: la declaración solo existe en la cuenta del convenio (HU-34). */
export type CuerpoSolicitud = Solicitud & Partial<Pick<SolicitudConvenio, 'declara_autorizacion'>>;
export type SolicitudRespuesta = components['schemas']['SolicitudRespuesta'];
export type Sentido = components['schemas']['SentidoEnum'];
export type ClientePortal = Client<paths>;

export function crearClientePortal(e: Entorno): ClientePortal {
  return createClient<paths>({ baseUrl: e.origen, fetch: (peticion: Request) => e.fetch(peticion) });
}

export const claves = {
  empresa: (slug: string) => ['portal', 'empresa', slug] as const,
};

export function useEmpresa(api: ClientePortal, slug: string) {
  return useQuery({
    queryKey: claves.empresa(slug),
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug } } })),
    // Sin reintentos automáticos: un 404 es la respuesta y una falla de red se reintenta con el botón.
    staleTime: 5 * 60_000,
  });
}

/** HU-34: registro público de la empresa cliente; queda en revisión. */
export type RegistroEmpresa = components['schemas']['RegistroConvenioRequest'];

export function useRegistrarEmpresa(api: ClientePortal, slug: string) {
  return useMutation({
    mutationFn: (datos: RegistroEmpresa) =>
      resultado(api.POST('/api/portal/{slug}/registro-empresa/', { params: { path: { slug } }, body: datos })),
  });
}

/** HU-35: cuenta opcional del pasajero; queda pendiente hasta confirmar por WhatsApp. */
export type CrearCuentaDatos = components['schemas']['CrearCuentaRequest'];

export function useCrearCuenta(api: ClientePortal, slug: string) {
  return useMutation({
    mutationFn: (datos: CrearCuentaDatos) =>
      resultado(api.POST('/api/portal/{slug}/cuenta/', { params: { path: { slug } }, body: datos })),
  });
}
