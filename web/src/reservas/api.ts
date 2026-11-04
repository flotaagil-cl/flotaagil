/**
 * Llamadas a /api/viajes/ (HU-03) y su caché en TanStack Query.
 *
 * Claves:
 *   ['viajes']                  todo
 *   ['viajes', 'lista', c]      un listado; c = consulta ya normalizada (mismos filtros → misma caché)
 *   ['viajes', 'detalle', id]   el detalle con su historial
 *
 * Crear, editar y cancelar dejan la respuesta (el detalle actualizado) en la caché del detalle e invalidan
 * los listados. Un 409 invalida el detalle y los listados para mostrar el estado real.
 */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components, paths } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type Viaje = components['schemas']['Viaje'];
export type ViajeDetalle = components['schemas']['ViajeDetalle'];
export type EstadoViaje = components['schemas']['EstadoViajeEnum'];
export type Sentido = components['schemas']['SentidoEnum'];
export type Canal = components['schemas']['CanalEnum'];
export type CanalPanel = components['schemas']['CanalPanelEnum'];
export type ViajeCrear = components['schemas']['ViajeCrearRequest'];
export type ViajeEditar = components['schemas']['PatchedViajeEditarRequest'];
export type ListaViajes = components['schemas']['PaginatedViajeList'];
export type ConsultaViajes = NonNullable<paths['/api/viajes/']['get']['parameters']['query']>;

export const claves = {
  todo: ['viajes'] as const,
  listas: ['viajes', 'lista'] as const,
  lista: (consulta: ConsultaViajes) => ['viajes', 'lista', consulta] as const,
  detalle: (id: number) => ['viajes', 'detalle', id] as const,
};

const VIGENCIA_MS = 30_000;
export const ESPERA_RESPUESTA_MS = 5_000;
export const ESPERA_VUELO_MS = 30_000;

export function useViajes(consulta: ConsultaViajes) {
  const api = useApi();
  return useQuery({
    queryKey: claves.lista(consulta),
    queryFn: () => resultado(api.GET('/api/viajes/', { params: { query: consulta } })),
    // Al cambiar de página o de filtro se mantiene a la vista el listado anterior mientras carga.
    placeholderData: keepPreviousData,
    staleTime: VIGENCIA_MS,
  });
}

export function useViaje(id: number) {
  const api = useApi();
  return useQuery({
    queryKey: claves.detalle(id),
    queryFn: () => resultado(api.GET('/api/viajes/{id}/', { params: { path: { id } } })),
    staleTime: VIGENCIA_MS,
    // HU-15: mientras espera la respuesta del conductor (60 s) se vuelve a pedir, para ver si aceptó, rechazó o venció.
    // HU-27: con vuelo se vuelve a pedir cada tanto, para ver una nueva propuesta de recogida.
    refetchInterval: (consulta) => {
      if (consulta.state.data?.estado === 'ASIGNADO') return ESPERA_RESPUESTA_MS;
      return consulta.state.data?.vuelo ? ESPERA_VUELO_MS : false;
    },
  });
}

function useAlTerminar() {
  const cliente = useQueryClient();
  return {
    exito(viaje: ViajeDetalle) {
      cliente.setQueryData(claves.detalle(viaje.id), viaje);
      void cliente.invalidateQueries({ queryKey: claves.listas });
    },
    error(id: number, error: Error) {
      if (error instanceof ErrorApi && error.estado === 409) {
        void cliente.invalidateQueries({ queryKey: claves.detalle(id) });
        void cliente.invalidateQueries({ queryKey: claves.listas });
      }
    },
  };
}

export function useCrearViaje() {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (datos: ViajeCrear) => resultado(api.POST('/api/viajes/', { body: datos })),
    onSuccess: alTerminar.exito,
  });
}

export function useEditarViaje(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (cambios: ViajeEditar) =>
      resultado(api.PATCH('/api/viajes/{id}/', { params: { path: { id } }, body: cambios })),
    onSuccess: alTerminar.exito,
    onError: (error) => alTerminar.error(id, error),
  });
}

export function useCancelarViaje(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (motivo: string) =>
      resultado(api.POST('/api/viajes/{id}/cancelar/', { params: { path: { id } }, body: { motivo } })),
    onSuccess: alTerminar.exito,
    onError: (error) => alTerminar.error(id, error),
  });
}

/** HU-27: el despachador confirma o descarta la nueva hora de recogida (RN-02). */
export function useDecidirRecogida(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: ({ confirmar, recogida_propuesta }: { confirmar: boolean; recogida_propuesta: string }) =>
      resultado(
        confirmar
          ? api.POST('/api/viajes/{id}/confirmar-recogida/', { params: { path: { id } }, body: { recogida_propuesta } })
          : api.POST('/api/viajes/{id}/descartar-recogida/', { params: { path: { id } }, body: { recogida_propuesta } }),
      ),
    onSuccess: alTerminar.exito,
    onError: (error) => alTerminar.error(id, error),
  });
}

export type Candidato = components['schemas']['Candidato'];

/** Conductores disponibles para asignar (HU-14). Se piden al abrir el diálogo y no se guardan mucho. */
export function useCandidatos(id: number, activo: boolean) {
  const api = useApi();
  return useQuery({
    queryKey: [...claves.detalle(id), 'candidatos'] as const,
    queryFn: () => resultado(api.GET('/api/viajes/{id}/candidatos/', { params: { path: { id } } })),
    enabled: activo,
    staleTime: 0,
  });
}

export function useAsignarViaje(id: number) {
  const api = useApi();
  const alTerminar = useAlTerminar();
  return useMutation({
    mutationFn: (conductor: number) =>
      resultado(api.POST('/api/viajes/{id}/asignar/', { params: { path: { id } }, body: { conductor } })),
    onSuccess: alTerminar.exito,
    onError: (error) => alTerminar.error(id, error),
  });
}
