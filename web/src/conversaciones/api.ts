/** HU-30 con HU-67 (CC-19): historial de WhatsApp en solo lectura. El canal se retiró: no llegan mensajes nuevos. */

import { keepPreviousData, useQuery } from '@tanstack/react-query';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type Conversacion = components['schemas']['Conversacion'];
export type ConversacionDetalle = components['schemas']['ConversacionDetalle'];
export type Mensaje = components['schemas']['Mensaje'];

export function useConversaciones(pagina: number) {
  const api = useApi();
  return useQuery({
    queryKey: ['conversaciones', 'lista', pagina],
    queryFn: () => resultado(api.GET('/api/conversaciones/', { params: { query: { page: pagina } } })),
    placeholderData: keepPreviousData,
  });
}

export function useConversacion(id: number) {
  const api = useApi();
  return useQuery({
    queryKey: ['conversaciones', 'hilo', id],
    queryFn: () => resultado(api.GET('/api/conversaciones/{id}/', { params: { path: { id } } })),
  });
}
