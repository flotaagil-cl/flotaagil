/** Administración de convenios (HU-11): solo el administrador. */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components, paths } from '../api/esquema';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type Convenio = components['schemas']['Convenio'];
export type ConvenioDetalle = components['schemas']['ConvenioDetalle'];
export type ConvenioCrear = NonNullable<paths['/api/convenios/']['post']['requestBody']>['content']['application/json'];
export type ConvenioEditar = NonNullable<paths['/api/convenios/{id}/']['patch']['requestBody']>['content']['application/json'];
export type ConsultaConvenios = NonNullable<paths['/api/convenios/']['get']['parameters']['query']>;

const claves = {
  todo: ['convenios'] as const,
  lista: (consulta: ConsultaConvenios) => ['convenios', 'lista', consulta] as const,
  detalle: (id: number) => ['convenios', 'detalle', id] as const,
};

export function useConvenios(consulta: ConsultaConvenios) {
  const api = useApi();
  return useQuery({
    queryKey: claves.lista(consulta),
    queryFn: () => resultado(api.GET('/api/convenios/', { params: { query: consulta } })),
    placeholderData: keepPreviousData,
  });
}

export function useConvenio(id: number) {
  const api = useApi();
  return useQuery({
    queryKey: claves.detalle(id),
    queryFn: () => resultado(api.GET('/api/convenios/{id}/', { params: { path: { id } } })),
  });
}

export type RegistroAuditoria = components['schemas']['RegistroAuditoria'];

/** HU-12: quién y cuándo cambió el convenio (RN-12). */
export function useAuditoriaConvenio(id: number, pagina: number) {
  const api = useApi();
  return useQuery({
    queryKey: ['convenios', 'auditoria', id, pagina],
    queryFn: () => resultado(api.GET('/api/convenios/{id}/auditoria/', { params: { path: { id }, query: { page: pagina } } })),
    placeholderData: keepPreviousData,
  });
}

export function useCrearConvenio() {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (datos: ConvenioCrear) => resultado(api.POST('/api/convenios/', { body: datos })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: claves.todo }),
  });
}

export function useEditarConvenio(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (cambios: ConvenioEditar) =>
      resultado(api.PATCH('/api/convenios/{id}/', { params: { path: { id } }, body: cambios })),
    onSuccess: (convenio) => {
      cliente.setQueryData(claves.detalle(id), convenio);
      void cliente.invalidateQueries({ queryKey: claves.todo });
    },
  });
}

type Accion = 'aprobar' | 'desactivar' | 'activar';

const RUTAS_ACCION = {
  aprobar: '/api/convenios/{id}/aprobar/',
  desactivar: '/api/convenios/{id}/desactivar/',
  activar: '/api/convenios/{id}/activar/',
} as const;

/** HU-34: aprobar, desactivar (RN-08) o reactivar. Quedan en auditoría (RN-12). */
export function useAccionConvenio(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (accion: Accion) => resultado(api.POST(RUTAS_ACCION[accion], { params: { path: { id } } })),
    onSuccess: (convenio) => {
      cliente.setQueryData(claves.detalle(id), convenio);
      void cliente.invalidateQueries({ queryKey: claves.todo });
    },
  });
}

export function useRechazarConvenio(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (motivo: string) =>
      resultado(api.POST('/api/convenios/{id}/rechazar/', { params: { path: { id } }, body: { motivo } })),
    onSuccess: (convenio) => {
      cliente.setQueryData(claves.detalle(id), convenio);
      void cliente.invalidateQueries({ queryKey: claves.todo });
    },
  });
}

/** DC-14: temporal que se muestra una vez. */
export function useRestablecerPassword(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: () => resultado(api.POST('/api/convenios/{id}/restablecer-password/', { params: { path: { id } } })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ['convenios', 'auditoria', id] }),
  });
}
