/** Chat de trabajo (HU-61, HU-62). El canal en vivo (/ws/chat/) invalida estas consultas; la revisión periódica es el respaldo. */

import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components } from '../api/esquema';
import { MENSAJES } from '../api/errores';
import { detalleDe, ErrorApi, resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type ConversacionChat = components['schemas']['ConversacionChat'];
export type MensajeChat = components['schemas']['MensajeChat'];
export type PersonaChat = components['schemas']['PersonaChat'];
export type Grupo = components['schemas']['Grupo'];

export const MAX_TEXTO = 1000;
const REVISION_MS = 30_000;

export const claves = {
  todo: ['chat'] as const,
  conversaciones: ['chat', 'conversaciones'] as const,
  mensajes: (id: number) => ['chat', 'mensajes', id] as const,
  grupo: (id: number) => ['chat', 'grupo', id] as const,
  personal: ['chat', 'personal'] as const,
  moderacion: ['chat', 'moderacion'] as const,
};

/** Mensaje de un error del chat: el `detail` del backend, el primer error de un campo o uno general. */
export function mensajeDelChat(error: unknown): string {
  if (!(error instanceof ErrorApi)) return MENSAJES.inesperado;
  const { estado, cuerpo } = error;
  if ([0, 502, 503, 504].includes(estado)) return MENSAJES.sin_conexion;
  if (estado === 429) return 'Estás enviando muchos mensajes seguidos. Espera un momento.';
  if (estado === 401) return MENSAJES.sesion_terminada;
  if (estado >= 500) return MENSAJES.error_servidor;
  const detalle = detalleDe(error);
  if (detalle) return detalle;
  const primero = cuerpo && typeof cuerpo === 'object' ? Object.values(cuerpo)[0] : null;
  if (Array.isArray(primero) && typeof primero[0] === 'string') return primero[0];
  if (typeof primero === 'string') return primero;
  return estado === 404 ? 'No se encontró.' : MENSAJES.inesperado;
}

/** Para las respuestas 204: basta con que la petición haya salido bien. */
async function sinCuerpo(llamada: Promise<{ response: Response; error?: unknown }>): Promise<void> {
  let respuesta: Awaited<typeof llamada>;
  try {
    respuesta = await llamada;
  } catch {
    throw new ErrorApi(0, null);
  }
  if (!respuesta.response.ok) throw new ErrorApi(respuesta.response.status, respuesta.error ?? null);
}

export function useConversacionesChat() {
  const api = useApi();
  return useQuery({
    queryKey: claves.conversaciones,
    queryFn: () => resultado(api.GET('/api/chat/conversaciones/')),
    refetchInterval: REVISION_MS,
  });
}

export function useMensajes(id: number) {
  const api = useApi();
  return useInfiniteQuery({
    queryKey: claves.mensajes(id),
    queryFn: ({ pageParam }) =>
      resultado(api.GET('/api/chat/conversaciones/{id}/mensajes/', { params: { path: { id }, query: pageParam ? { antes: pageParam } : {} } })),
    initialPageParam: 0,
    getNextPageParam: (pagina) => (pagina.hay_mas && pagina.results.length ? pagina.results[0].id : undefined),
  });
}

export function useEscribir(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { texto?: string; rapida?: components['schemas']['RapidaEnum'] }) =>
      resultado(api.POST('/api/chat/conversaciones/{id}/mensajes/', { params: { path: { id } }, body: cuerpo })),
    onSettled: () => {
      void cliente.invalidateQueries({ queryKey: claves.mensajes(id) });
      void cliente.invalidateQueries({ queryKey: claves.conversaciones });
    },
  });
}

export function useMarcarLeido(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (hasta: number) => sinCuerpo(api.POST('/api/chat/conversaciones/{id}/leido/', { params: { path: { id } }, body: { hasta } })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: claves.conversaciones }),
  });
}

export function usePersonal(activo: boolean) {
  const api = useApi();
  return useQuery({ queryKey: claves.personal, queryFn: () => resultado(api.GET('/api/chat/personal/')), enabled: activo });
}

export function useNuevoDirecto() {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (usuario: number) => resultado(api.POST('/api/chat/directos/', { body: { usuario } })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: claves.conversaciones }),
  });
}

export function useNuevoGrupo() {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { nombre: string; ids_integrantes: number[] }) => resultado(api.POST('/api/chat/grupos/', { body: cuerpo })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: claves.conversaciones }),
  });
}

export function useGrupo(id: number | null) {
  const api = useApi();
  return useQuery({
    queryKey: claves.grupo(id ?? 0),
    queryFn: () => resultado(api.GET('/api/chat/grupos/{id}/', { params: { path: { id: id! } } })),
    enabled: id !== null,
  });
}

/** Renombrar, agregar, quitar y borrar: al terminar se vuelve a pedir todo el chat (también la moderación). */
export function useGestionGrupo(id: number) {
  const api = useApi();
  const cliente = useQueryClient();
  const alTerminar = () => void cliente.invalidateQueries({ queryKey: claves.todo });
  const ruta = { params: { path: { id } } };
  return {
    renombrar: useMutation({
      mutationFn: (nombre: string) => resultado(api.PATCH('/api/chat/grupos/{id}/', { ...ruta, body: { nombre } })),
      onSuccess: alTerminar,
    }),
    agregar: useMutation({
      mutationFn: (usuario: number) => resultado(api.POST('/api/chat/grupos/{id}/integrantes/', { ...ruta, body: { usuario } })),
      onSuccess: alTerminar,
    }),
    quitar: useMutation({
      mutationFn: (usuario: number) =>
        sinCuerpo(api.DELETE('/api/chat/grupos/{id}/integrantes/{usuario_id}/', { params: { path: { id, usuario_id: usuario } } })),
      onSuccess: alTerminar,
    }),
    borrar: useMutation({
      mutationFn: () => sinCuerpo(api.DELETE('/api/chat/grupos/{id}/', ruta)),
      onSuccess: alTerminar,
    }),
  };
}

export function useModeracion() {
  const api = useApi();
  return useQuery({ queryKey: claves.moderacion, queryFn: () => resultado(api.GET('/api/chat/moderacion/grupos/')) });
}
