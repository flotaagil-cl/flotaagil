import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { resultado } from '../api/resultado';
import { useEntorno } from '../entornoContexto';
import type { CrearSocket } from '../mapa/conexion';
import { ESTADOS } from '../reservas/etiquetas';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { ConexionIndicadores, type FaseIndicadores } from './conexionIndicadores';
import estilos from './Inicio.module.css';

const CLAVE = ['indicadores'];
// Perder la señal no genera ningún aviso (es que no llegan posiciones), y tampoco el cambio de día.
const REVISION_MS = 15_000;

const TEXTO_FASE: Record<FaseIndicadores, string> = {
  conectando: 'Conectando…',
  en_vivo: 'En vivo',
  reconectando: 'Reconectando: los datos pueden tener hasta 15 s',
  sin_sesion: 'La sesión terminó.',
};

/** HU-01: reservas del día por estado y vehículos en línea, sin recargar. `crearSocket` se reemplaza en las pruebas. */
export function Indicadores({ crearSocket }: { crearSocket?: CrearSocket }) {
  const api = useApi();
  const entorno = useEntorno();
  const { sesion } = useSesion();
  const cliente = useQueryClient();
  const [fase, setFase] = useState<FaseIndicadores>('conectando');
  const consulta = useQuery({
    queryKey: CLAVE,
    queryFn: () => resultado(api.GET('/api/indicadores/')),
    refetchInterval: REVISION_MS,
  });
  const conexion = useMemo(
    () =>
      new ConexionIndicadores(
        `${entorno.origen.replace(/^http/, 'ws')}/ws/indicadores/`,
        sesion,
        () => void cliente.invalidateQueries({ queryKey: CLAVE }),
        setFase,
        crearSocket,
      ),
    [entorno, sesion, cliente, crearSocket],
  );

  useEffect(() => {
    conexion.iniciar();
    return () => conexion.detener();
  }, [conexion]);

  return (
    <section className={estilos.indicadores} aria-labelledby="titulo-indicadores">
      <div className={estilos.tituloIndicadores}>
        <h2 id="titulo-indicadores">Hoy</h2>
        <span aria-live="polite">{TEXTO_FASE[fase]}</span>
      </div>
      {consulta.isPending ? (
        <p>Cargando indicadores…</p>
      ) : consulta.isError ? (
        <div role="alert">
          <p>No se pudieron cargar los indicadores.</p>
          <button type="button" onClick={() => void consulta.refetch()}>
            Reintentar
          </button>
        </div>
      ) : (
        <>
          <dl className={estilos.cifras} aria-label="Vehículos">
            <div>
              <dt>En línea con señal</dt>
              <dd>{consulta.data.vehiculos.en_linea_con_senal}</dd>
            </div>
            <div>
              <dt>En línea sin señal</dt>
              <dd>{consulta.data.vehiculos.en_linea_sin_senal}</dd>
            </div>
            <div>
              <dt>Vehículos fuera de línea</dt>
              <dd>{consulta.data.vehiculos.fuera_de_linea}</dd>
            </div>
            <div>
              <dt>Reservas del día</dt>
              <dd>{consulta.data.reservas.total}</dd>
            </div>
          </dl>
          <ul className={estilos.porEstado} aria-label="Reservas del día por estado">
            {consulta.data.reservas.por_estado.map(({ estado, cantidad }) => (
              <li key={estado}>
                <Link to={`/reservas?fecha=${consulta.data.fecha}&estado=${estado}`}>
                  <span>{ESTADOS[estado]}</span>
                  <strong>{cantidad}</strong>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
