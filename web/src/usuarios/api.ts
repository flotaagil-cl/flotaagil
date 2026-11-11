/** HU-36: usuarios del panel (administradores y despachadores). Solo el administrador. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type UsuarioPanel = components['schemas']['UsuarioPanel'];
export type RolPanel = 'ADMINISTRADOR' | 'DESPACHADOR';

const CLAVE = ['usuarios-panel'] as const;

export function useUsuarios() {
  const api = useApi();
  return useQuery({ queryKey: CLAVE, queryFn: () => resultado(api.GET('/api/usuarios/')) });
}

function useRefrescar() {
  const cliente = useQueryClient();
  return () => void cliente.invalidateQueries({ queryKey: CLAVE });
}

export function useCrearUsuario() {
  const api = useApi();
  const refrescar = useRefrescar();
  return useMutation({
    mutationFn: (datos: { nombre: string; email: string; rol: RolPanel }) => resultado(api.POST('/api/usuarios/', { body: datos })),
    onSuccess: refrescar,
  });
}

export function useEditarUsuario() {
  const api = useApi();
  const refrescar = useRefrescar();
  return useMutation({
    mutationFn: ({ id, ...cambios }: { id: number; nombre?: string; rol?: RolPanel }) =>
      resultado(api.PATCH('/api/usuarios/{id}/', { params: { path: { id } }, body: cambios })),
    onSuccess: refrescar,
  });
}

export function useAccionUsuario() {
  const api = useApi();
  const refrescar = useRefrescar();
  return useMutation({
    mutationFn: ({ id, accion }: { id: number; accion: 'desactivar' | 'activar' }) =>
      resultado(
        accion === 'desactivar'
          ? api.POST('/api/usuarios/{id}/desactivar/', { params: { path: { id } } })
          : api.POST('/api/usuarios/{id}/activar/', { params: { path: { id } } }),
      ),
    onSuccess: refrescar,
  });
}

export function useRestablecerUsuario() {
  const api = useApi();
  const refrescar = useRefrescar();
  return useMutation({
    mutationFn: (id: number) => resultado(api.POST('/api/usuarios/{id}/password/', { params: { path: { id } } })),
    onSuccess: refrescar,
  });
}
