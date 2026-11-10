/** HU-31 (CC-12): turnos por cerrar y cierre de caja. Solo el administrador. */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type TurnoPorCerrar = components['schemas']['TurnoPorCerrar'];
export type CierreCaja = components['schemas']['CierreCaja'];

const CLAVE = ['caja', 'por-cerrar'] as const;

export function useTurnosPorCerrar() {
  const api = useApi();
  return useQuery({ queryKey: CLAVE, queryFn: () => resultado(api.GET('/api/turnos/por-cerrar/')) });
}

export function useCerrarCaja(turno: number) {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation({
    mutationFn: (cuerpo: { monto_rendido: number; observacion?: string }) =>
      resultado(api.POST('/api/turnos/{id}/cierre-caja/', { params: { path: { id: turno } }, body: cuerpo })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: CLAVE }),
  });
}
