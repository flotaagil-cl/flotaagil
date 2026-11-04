import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import { resultado } from '../api/resultado';
import { useApi } from '../sesion/SesionProvider';
import { sonarAlerta } from './sonido';
import estilos from './alertas.module.css';

/** Cada cuánto se revisan. El vuelo se consulta como mucho cada 10 min: no hace falta un canal en vivo. */
export const REVISION_MS = 15_000;

const CLAVE = ['alertas', 'pendientes'] as const;
const TITULOS = {
  ETA_CAMBIADA: 'Cambió la llegada del vuelo',
  VUELO_CANCELADO: 'Vuelo cancelado',
  VUELO_DESVIADO: 'Vuelo desviado',
  SIN_DATOS: 'Vuelo sin datos',
} as const;

/** HU-28: alerta visual y sonora en todo el panel. Cada alerta enlaza a su reserva y se marca como atendida. */
export function AlertasVuelo() {
  const api = useApi();
  const cliente = useQueryClient();
  const [falla, setFalla] = useState(false);
  const consulta = useQuery({
    queryKey: CLAVE,
    queryFn: () => resultado(api.GET('/api/alertas/', { params: { query: { pendientes: true } } })),
    refetchInterval: REVISION_MS,
    retry: false,
  });
  const atender = useMutation({
    mutationFn: (id: number) => resultado(api.POST('/api/alertas/{id}/atender/', { params: { path: { id } } })),
    onSuccess: () => {
      setFalla(false);
      void cliente.invalidateQueries({ queryKey: CLAVE });
      void cliente.invalidateQueries({ queryKey: ['viajes'] });
    },
    onError: () => setFalla(true),
  });

  const alertas = consulta.data?.results ?? [];
  const conocidas = useRef<Set<number> | null>(null);
  const ids = alertas.map((a) => a.id).join(',');
  useEffect(() => {
    if (!consulta.isSuccess) return;
    const actuales = new Set(ids ? ids.split(',').map(Number) : []);
    // Lo que ya estaba al abrir el panel se ve, pero no suena. Lo nuevo suena y refresca las reservas.
    if (conocidas.current && [...actuales].some((id) => !conocidas.current?.has(id))) {
      sonarAlerta();
      void cliente.invalidateQueries({ queryKey: ['viajes'] });
    }
    conocidas.current = actuales;
  }, [consulta.isSuccess, ids, cliente]);

  if (alertas.length === 0) return null;
  return (
    <section className={estilos.alertas} aria-label="Alertas de vuelos" role="alert">
      {falla && <p>No se pudo marcar la alerta. Intenta de nuevo.</p>}
      <ul>
        {alertas.map((alerta) => (
          <li key={alerta.id}>
            <span>
              <strong>{TITULOS[alerta.tipo]}</strong> · {alerta.detalle}{' '}
              <Link to={`/reservas/${alerta.viaje}`}>Ver reserva #{alerta.viaje}</Link>
            </span>
            <button type="button" disabled={atender.isPending} aria-label={`Marcar como atendida la alerta de la reserva ${alerta.viaje}`} onClick={() => atender.mutate(alerta.id)}>
              Atendida
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
