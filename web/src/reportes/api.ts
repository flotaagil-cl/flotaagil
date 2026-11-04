/** Reportes operativos (HU-06): solo el administrador. */

import { useMutation, useQuery } from '@tanstack/react-query';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';

export type Reporte = components['schemas']['Reporte'];
export type Columna = components['schemas']['Columna'];
export type TipoReporte = 'liquidacion' | 'facturacion' | 'cancelaciones' | 'historial';

export interface FiltrosReporte {
  desde: string;
  hasta: string;
  conductor?: number;
  convenio?: number;
}

export function useReporte(tipo: TipoReporte, filtros: FiltrosReporte, pagina: number, habilitado: boolean) {
  const api = useApi();
  const query = { ...filtros, ...(pagina > 1 && { page: pagina }) };
  return useQuery({
    queryKey: ['reportes', tipo, query],
    queryFn: () => resultado(api.GET('/api/reportes/{tipo}/', { params: { path: { tipo }, query } })),
    // Dentro del mismo reporte evita el parpadeo; los datos de otro reporte no se muestran bajo su título.
    placeholderData: (anterior, consultaAnterior) => (consultaAnterior?.queryKey[1] === tipo ? anterior : undefined),
    enabled: habilitado,
  });
}

export function useOpcionesReporte() {
  const api = useApi();
  return useQuery({
    queryKey: ['reportes', 'opciones'],
    queryFn: () => resultado(api.GET('/api/reportes/opciones/')),
    staleTime: 60_000,
  });
}

/** Descarga con el access de la sesión: un enlace directo no lo llevaría. */
export function useDescargarCsv() {
  const api = useApi();
  return useMutation({
    mutationFn: async ({ tipo, filtros }: { tipo: TipoReporte; filtros: FiltrosReporte }) => {
      const archivo = await resultado(
        api.GET('/api/reportes/{tipo}/csv/', { params: { path: { tipo }, query: filtros }, parseAs: 'blob' }),
      );
      const url = URL.createObjectURL(archivo as Blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `${tipo}-${filtros.desde}-${filtros.hasta}.csv`;
      document.body.append(enlace);
      enlace.click();
      enlace.remove();
      URL.revokeObjectURL(url);
    },
  });
}
