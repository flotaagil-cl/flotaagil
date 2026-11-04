/** Chat de WhatsApp (HU-30). La revisión periódica trae los mensajes nuevos: el backend no los empuja al panel. */

import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type Conversacion = components['schemas']['Conversacion'];
export type ConversacionDetalle = components['schemas']['ConversacionDetalle'];
export type Mensaje = components['schemas']['Mensaje'];

const REVISION_BANDEJA_MS = 15_000;
const REVISION_HILO_MS = 5_000;

export function useConversaciones(pagina: number) {
  const api = useApi();
  return useQuery({
    queryKey: ['conversaciones', 'lista', pagina],
    queryFn: () => resultado(api.GET('/api/conversaciones/', { params: { query: { page: pagina } } })),
    placeholderData: keepPreviousData,
    refetchInterval: REVISION_BANDEJA_MS,
  });
}

export function useConversacion(id: number) {
  const api = useApi();
  return useQuery({
    queryKey: ['conversaciones', 'hilo', id],
    queryFn: () => resultado(api.GET('/api/conversaciones/{id}/', { params: { path: { id } } })),
    refetchInterval: REVISION_HILO_MS,
  });
}

export function useResponder(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (texto: string) =>
      resultado(api.POST('/api/conversaciones/{id}/mensajes/', { params: { path: { id } }, body: { texto } })),
    onSettled: () => void cliente.invalidateQueries({ queryKey: ['conversaciones'] }),
  });
}
