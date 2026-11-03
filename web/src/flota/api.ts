/**
 * Llamadas a /api/vehiculos/ y /api/conductores/ (HU-10) y su caché en TanStack Query.
 *
 * Claves:
 *   ['vehiculos', 'lista', c] · ['vehiculos', 'detalle', id]
 *   ['conductores', 'lista', c] · ['conductores', 'detalle', id]
 *
 * Una escritura deja la respuesta en la caché del detalle e invalida los listados de ambos: el listado de
 * vehículos muestra sus conductores y el de conductores, sus vehículos.
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components, paths } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type Vehiculo = components['schemas']['Vehiculo'];
export type VehiculoCrear = components['schemas']['VehiculoCrearRequest'];
export type VehiculoEditar = components['schemas']['PatchedVehiculoEditarRequest'];
export type Conductor = components['schemas']['Conductor'];
export type ConductorEditar = components['schemas']['PatchedConductorEditarRequest'];
export type EstadoConductor = components['schemas']['ConductorEstadoEnum'];
export type LicenciaClase = components['schemas']['LicenciaClaseEnum'];
export type Informe = components['schemas']['InformeImportacion'];
export type ConsultaVehiculos = NonNullable<paths['/api/vehiculos/']['get']['parameters']['query']>;
export type ConsultaConductores = NonNullable<paths['/api/conductores/']['get']['parameters']['query']>;

export const claves = {
  vehiculos: ['vehiculos'] as const,
  listaVehiculos: (c: ConsultaVehiculos) => ['vehiculos', 'lista', c] as const,
  vehiculo: (id: number) => ['vehiculos', 'detalle', id] as const,
  conductores: ['conductores'] as const,
  listaConductores: (c: ConsultaConductores) => ['conductores', 'lista', c] as const,
  conductor: (id: number) => ['conductores', 'detalle', id] as const,
};

const VIGENCIA_MS = 30_000;

export function useVehiculos(consulta: ConsultaVehiculos) {
  const api = useApi();
  return useQuery({
    queryKey: claves.listaVehiculos(consulta),
    queryFn: () => resultado(api.GET('/api/vehiculos/', { params: { query: consulta } })),
    placeholderData: keepPreviousData,
    staleTime: VIGENCIA_MS,
  });
}

export function useVehiculo(id: number) {
  const api = useApi();
  return useQuery({
    queryKey: claves.vehiculo(id),
    queryFn: () => resultado(api.GET('/api/vehiculos/{id}/', { params: { path: { id } } })),
    staleTime: VIGENCIA_MS,
  });
}

export function useConductores(consulta: ConsultaConductores) {
  const api = useApi();
  return useQuery({
    queryKey: claves.listaConductores(consulta),
    queryFn: () => resultado(api.GET('/api/conductores/', { params: { query: consulta } })),
    placeholderData: keepPreviousData,
    staleTime: VIGENCIA_MS,
  });
}

export function useConductor(id: number) {
  const api = useApi();
  return useQuery({
    queryKey: claves.conductor(id),
    queryFn: () => resultado(api.GET('/api/conductores/{id}/', { params: { path: { id } } })),
    staleTime: VIGENCIA_MS,
  });
}

/** Tras escribir: el detalle queda con la respuesta y los listados de vehículos y conductores se recargan. */
function useAlTerminar() {
  const cliente = useQueryClient();
  return {
    vehiculo(vehiculo: Vehiculo) {
      cliente.setQueryData(claves.vehiculo(vehiculo.id), vehiculo);
      void cliente.invalidateQueries({ queryKey: [...claves.vehiculos, 'lista'] });
      void cliente.invalidateQueries({ queryKey: claves.conductores });
    },
    conductor(conductor: Conductor) {
      cliente.setQueryData(claves.conductor(conductor.id), conductor);
      void cliente.invalidateQueries({ queryKey: [...claves.conductores, 'lista'] });
      void cliente.invalidateQueries({ queryKey: claves.vehiculos });
    },
    /** Un 409 recarga el detalle para mostrar el estado real. */
    conflicto(error: Error, clave: readonly unknown[]) {
      if (error instanceof ErrorApi && error.estado === 409) void cliente.invalidateQueries({ queryKey: clave });
    },
  };
}

export function useCrearVehiculo() {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (datos: VehiculoCrear) => resultado(api.POST('/api/vehiculos/', { body: datos })),
    onSuccess: alTerminar.vehiculo,
  });
}

export function useEditarVehiculo(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (cambios: VehiculoEditar) =>
      resultado(api.PATCH('/api/vehiculos/{id}/', { params: { path: { id } }, body: cambios })),
    onSuccess: alTerminar.vehiculo,
    onError: (error) => alTerminar.conflicto(error, claves.vehiculo(id)),
  });
}

/** Carga por CSV: sin `confirmar` solo trae el informe; con `confirmar`, crea todo o nada. */
export function useImportarVehiculos() {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: ({ archivo, confirmar }: { archivo: File; confirmar: boolean }) =>
      resultado(
        api.POST('/api/vehiculos/importar/', {
          // El esquema tipa el archivo como string (binary); el cuerpo real es multipart.
          body: { archivo: archivo as unknown as string, confirmar },
          bodySerializer: () => {
            const formulario = new FormData();
            formulario.append('archivo', archivo);
            formulario.append('confirmar', String(confirmar));
            return formulario;
          },
        }),
      ),
    onSuccess: (informe) => {
      if (informe.creados > 0) void cliente.invalidateQueries({ queryKey: claves.vehiculos });
    },
  });
}

export function useEditarConductor(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (cambios: ConductorEditar) =>
      resultado(api.PATCH('/api/conductores/{id}/', { params: { path: { id } }, body: cambios })),
    onSuccess: alTerminar.conductor,
  });
}

export function useAsociarVehiculo(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (vehiculo: number) =>
      resultado(api.POST('/api/conductores/{id}/vehiculos/', { params: { path: { id } }, body: { vehiculo } })),
    onSuccess: alTerminar.conductor,
  });
}

export function useQuitarVehiculo(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (vehiculo: number) =>
      resultado(
        api.DELETE('/api/conductores/{id}/vehiculos/{vehiculo_id}/', {
          params: { path: { id, vehiculo_id: String(vehiculo) } },
        }),
      ),
    onSuccess: alTerminar.conductor,
    onError: (error) => alTerminar.conflicto(error, claves.conductor(id)),
  });
}
