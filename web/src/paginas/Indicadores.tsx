import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { Icono } from '../diseno/Icono';
import { useEntorno } from '../entornoContexto';
import type { CrearSocket } from '../mapa/conexion';
import { ESTADOS } from '../reservas/etiquetas';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { ConexionIndicadores, TEXTO_FASE, type FaseIndicadores } from './conexionIndicadores';
import estilos from './Inicio.module.css';

type EstadoViaje = components['schemas']['EstadoViajeEnum'];

const CLAVE = ['indicadores'];
// Perder la señal no genera ningún aviso (es que no llegan posiciones), y tampoco el cambio de día.
const REVISION_MS = 15_000;

const TONO_ESTADO: Record<EstadoViaje, 'aviso' | 'esmeralda' | 'ok' | 'peligro'> = {
  PENDIENTE_CONFIRMACION: 'aviso',
  SOLICITADO: 'aviso',
  ASIGNADO: 'esmeralda',
  ACEPTADO: 'esmeralda',
  EN_CAMINO: 'esmeralda',
  EN_ZONA: 'esmeralda',
  PASAJERO_A_BORDO: 'esmeralda',
  FINALIZADO: 'ok',
  CANCELADO: 'peligro',
};

interface Props {
  crearSocket?: CrearSocket;
  alCambiarFase?: (fase: FaseIndicadores) => void;
}

/** HU-01: reservas del día por estado y vehículos en línea, sin recargar. `crearSocket` se reemplaza en las pruebas. */
export function Indicadores({ crearSocket, alCambiarFase }: Props) {
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
        (nueva) => {
          setFase(nueva);
          alCambiarFase?.(nueva);
        },
        crearSocket,
      ),
    [entorno, sesion, cliente, crearSocket, alCambiarFase],
  );

  useEffect(() => {
    conexion.iniciar();
    return () => conexion.detener();
  }, [conexion]);

  return (
    <section className={estilos.indicadores} aria-labelledby="titulo-indicadores">
      {!alCambiarFase && (
        <div className={estilos.tituloIndicadores}>
          <span aria-live="polite">{TEXTO_FASE[fase]}</span>
        </div>
      )}
      {consulta.isPending ? (
        <p className={estilos.estadoCarga}>Cargando indicadores…</p>
      ) : consulta.isError ? (
        <div className={estilos.alertaError} role="alert">
          <p>No se pudieron cargar los indicadores.</p>
          <button type="button" className={estilos.botonReintentar} onClick={() => void consulta.refetch()}>
            Reintentar
          </button>
        </div>
      ) : (
        <>
          {consulta.data.sin_confirmar > 0 && (
            <p className={estilos.alertaSinConfirmar} role="alert">
              <Icono nombre="alerta" tamano={18} className={estilos.iconoAlerta} />
              <span>
                <Link to="/reservas?sin_confirmar=true&desde=">
                  {consulta.data.sin_confirmar === 1 ? '1 reserva sin confirmar' : `${consulta.data.sin_confirmar} reservas sin confirmar`}
                </Link>
                : venció su plazo. Confírmalas por teléfono o cancélalas.
              </span>
            </p>
          )}

          {/* Bloque 1: KPIs principales */}
          <dl className={estilos.cifras} aria-label="Vehículos">
            <div className={estilos.kpi} data-tono="ok">
              <dt>En línea con señal</dt>
              <dd>{consulta.data.vehiculos.en_linea_con_senal}</dd>
            </div>
            <div className={estilos.kpi} data-tono="aviso">
              <dt>En línea sin señal</dt>
              <dd>{consulta.data.vehiculos.en_linea_sin_senal}</dd>
            </div>
            <div className={estilos.kpi} data-tono="neutro">
              <dt>Vehículos fuera de línea</dt>
              <dd>{consulta.data.vehiculos.fuera_de_linea}</dd>
            </div>
            <div className={estilos.kpi} data-tono="esmeralda">
              <dt>Reservas del día</dt>
              <dd>{consulta.data.reservas.total}</dd>
            </div>
          </dl>

          {/* Bloque 2: Flujo de reservas del día */}
          <div className={estilos.flujoTarjeta}>
            <div className={estilos.flujoCabecera}>
              <h2 id="titulo-indicadores">Flujo de reservas hoy</h2>
              <span className={estilos.flujoResumen}>
                {consulta.data.reservas.total === 1 ? '1 reserva en total' : `${consulta.data.reservas.total} reservas en total`}
              </span>
            </div>
            <ul className={estilos.porEstado} aria-label="Reservas del día por estado">
              {consulta.data.reservas.por_estado.map(({ estado, cantidad }) => (
                <li key={estado}>
                  <Link
                    to={`/reservas?fecha=${consulta.data.fecha}&estado=${estado}`}
                    className={estilos.chipEstado}
                    data-activo={cantidad > 0}
                    data-tono={cantidad > 0 ? TONO_ESTADO[estado] : 'cero'}
                  >
                    <span className={estilos.nombreEstado}>{ESTADOS[estado]}</span>
                    <strong className={estilos.contadorEstado}>{cantidad}</strong>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </>
      )}
    </section>
  );
}
