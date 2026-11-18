/**
 * HU-69: «Vuelos de hoy» (administrador y despachador). Viajes de aeropuerto del día de la empresa, ordenados por la
 * hora del vuelo, con contadores, filtros y la propuesta de recogida confirmable desde la fila (RN-02). Se actualiza
 * sola cada minuto y solo lee la base: el monitoreo (HU-27) es el único que consulta la API de vuelos.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Link } from 'react-router';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import estilos from '../componentes/panel.module.css';
import campos from '../formularios/formularios.module.css';
import { Segmentado } from '../diseno/Segmentado';
import { FallaDeCarga } from '../flota/componentes/comunes';
import { formatearFecha, formatearHora } from '../hora/hora';
import { useDecidirRecogida } from '../reservas/api';
import { mensajeDeErrorApi } from '../reservas/errores';
import { ESTADOS_VUELO } from '../reservas/etiquetas';
import { useApi } from '../sesion/SesionProvider';
import { EstadoVuelo } from './LineaVuelo';
import { useAhora } from './useAhora';
import { cuentaRegresiva, enEspera, estadoDeVuelo, llegadaDe, minutosHasta, tipoDeSalida } from './textos';
import c from './vuelos.module.css';

type Viaje = components['schemas']['Viaje'];
type EstadoVueloApi = components['schemas']['EstadoVueloEnum'];
type Tipo = 'todos' | 'llegadas' | 'salidas';

export const REFRESCO_MS = 60_000;

const TIPOS: { valor: Tipo; texto: string }[] = [
  { valor: 'todos', texto: 'Todos' },
  { valor: 'llegadas', texto: 'Llegadas' },
  { valor: 'salidas', texto: 'Salidas' },
];

export function VuelosDeHoy() {
  const api = useApi();
  const ahora = useAhora();
  const [tipo, setTipo] = useState<Tipo>('todos');
  const [estado, setEstado] = useState<EstadoVueloApi | ''>('');
  const consulta = useQuery({
    queryKey: ['vuelos-de-hoy', tipo, estado],
    queryFn: () =>
      resultado(
        api.GET('/api/vuelos-de-hoy/', {
          params: { query: { ...(tipo !== 'todos' && { tipo }), ...(estado && { estado }) } },
        }),
      ),
    refetchInterval: REFRESCO_MS,
    placeholderData: (anterior) => anterior,
  });

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Vuelos de hoy</h1>
      </div>
      <p className={estilos.explicacion}>
        {consulta.data ? `${formatearFecha(consulta.data.fecha)} · ` : ''}Se actualiza cada minuto con lo que registró el monitoreo de vuelos.
      </p>
      {consulta.isPending ? (
        <Cargando />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="los vuelos de hoy" reintentar={() => void consulta.refetch()} />
      ) : (
        <>
          <ul className={c.contadores} aria-label="Resumen del día">
            <Contador valor={consulta.data.contadores.demorados} texto="demorados" />
            <Contador valor={consulta.data.contadores.cancelados_o_desviados} texto="cancelados o desviados" />
            <Contador valor={consulta.data.contadores.sin_conductor} texto="sin conductor" />
            <Contador valor={consulta.data.contadores.propuestas_pendientes} texto="propuestas de recogida pendientes" />
          </ul>
          <div className={c.filtros}>
            <Segmentado etiqueta="Mostrar" opciones={TIPOS} valor={tipo} onCambiar={(nuevo) => setTipo(nuevo)} forma="pastillas" />
            <label className={campos.campo}>
              Estado del vuelo
              <select value={estado} disabled={tipo === 'salidas'} onChange={(e) => setEstado(e.target.value as EstadoVueloApi | '')}>
                <option value="">Todos</option>
                {Object.entries(ESTADOS_VUELO).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {consulta.data.viajes.length === 0 ? (
            <div className={estilos.vacio}>
              <p>No hay vuelos con estos filtros hoy.</p>
            </div>
          ) : (
            <table className={estilos.tabla} aria-label="Vuelos de hoy" aria-busy={consulta.isFetching || undefined}>
              <thead>
                <tr>
                  <th scope="col">Vuelo</th>
                  <th scope="col">Programada</th>
                  <th scope="col">Estimada</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Cuenta regresiva</th>
                  <th scope="col">Pasajero</th>
                  <th scope="col">Conductor</th>
                  <th scope="col">Recogida</th>
                </tr>
              </thead>
              <tbody>
                {consulta.data.viajes.map((viaje) => (
                  <Fila key={viaje.id} viaje={viaje} ahora={ahora} />
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}

function Contador({ valor, texto }: { valor: number; texto: string }) {
  return (
    <li className={c.contador} data-atencion={valor > 0 || undefined}>
      <strong>{valor}</strong> {texto}
    </li>
  );
}

function Fila({ viaje, ahora }: { viaje: Viaje; ahora: number }) {
  const vuelo = viaje.vuelo;
  const detalle = `/reservas/${viaje.id}`;
  const conductor = viaje.conductor ? viaje.conductor.nombre : <span className={c.sinAsignar}>Sin asignar</span>;

  if (vuelo) {
    const llegada = llegadaDe(vuelo);
    const regresiva =
      vuelo.estado_vuelo === 'ATERRIZADO'
        ? `aterrizó ${cuentaRegresiva(llegada, Math.max(ahora, Date.parse(llegada)))}`
        : enEspera(vuelo) && minutosHasta(llegada, ahora) > 0
          ? `aterriza ${cuentaRegresiva(llegada, ahora)}`
          : '—';
    return (
      <tr>
        <Celda titulo="Vuelo">
          <Link to={detalle}>{vuelo.numero}</Link>
          <span className={estilos.secundario}>Llegada · reserva #{viaje.id}</span>
        </Celda>
        <Celda titulo="Programada">{formatearHora(vuelo.hora_programada, ahora)}</Celda>
        <Celda titulo="Estimada">{vuelo.hora_estimada ? formatearHora(vuelo.hora_estimada, ahora) : '—'}</Celda>
        <Celda titulo="Estado">
          <EstadoVuelo estado={estadoDeVuelo(vuelo, ahora)} />
        </Celda>
        <Celda titulo="Cuenta regresiva">{regresiva}</Celda>
        <Celda titulo="Pasajero">{viaje.pasajero.nombre}</Celda>
        <Celda titulo="Conductor">{conductor}</Celda>
        <Celda titulo="Recogida">
          {vuelo.recogida_propuesta ? <PropuestaEnFila viaje={viaje} propuesta={vuelo.recogida_propuesta} ahora={ahora} /> : formatearHora(viaje.recogida_en, ahora)}
        </Celda>
      </tr>
    );
  }

  const despegue = viaje.vuelo_salida_en ?? viaje.recogida_en;
  return (
    <tr>
      <Celda titulo="Vuelo">
        <Link to={detalle}>Salida{tipoDeSalida(viaje)}</Link>
        <span className={estilos.secundario}>Reserva #{viaje.id}</span>
      </Celda>
      <Celda titulo="Programada">{formatearHora(despegue, ahora)}</Celda>
      <Celda titulo="Estimada">—</Celda>
      <Celda titulo="Estado">
        <span className={estilos.secundario}>No se monitorea</span>
      </Celda>
      <Celda titulo="Cuenta regresiva">{minutosHasta(despegue, ahora) > 0 ? `despega ${cuentaRegresiva(despegue, ahora)}` : '—'}</Celda>
      <Celda titulo="Pasajero">{viaje.pasajero.nombre}</Celda>
      <Celda titulo="Conductor">{conductor}</Celda>
      <Celda titulo="Recogida">
        {formatearHora(viaje.recogida_en, ahora)}
        {viaje.en_aeropuerto_a_las && (
          <span className={estilos.secundario}>Debe estar en el aeropuerto a las {formatearHora(viaje.en_aeropuerto_a_las, ahora)}</span>
        )}
      </Celda>
    </tr>
  );
}

/** La propuesta de HU-27 se confirma o se descarta desde la fila; la recogida no cambia sin confirmación (RN-02). */
function PropuestaEnFila({ viaje, propuesta, ahora }: { viaje: Viaje; propuesta: string; ahora: number }) {
  const decidir = useDecidirRecogida(viaje.id);
  const consultas = useQueryClient();
  const [falla, setFalla] = useState<string | null>(null);

  async function resolver(confirmar: boolean) {
    setFalla(null);
    try {
      await decidir.mutateAsync({ confirmar, recogida_propuesta: propuesta });
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    } finally {
      void consultas.invalidateQueries({ queryKey: ['vuelos-de-hoy'] });
    }
  }

  return (
    <>
      {formatearHora(viaje.recogida_en, ahora)}
      <span className={`${c.aviso} ${c.bloque}`}>⚠ propuesta {formatearHora(propuesta, ahora)} sin confirmar</span>
      <span className={c.botonesFila}>
        <button
          type="button"
          className={estilos.boton}
          disabled={decidir.isPending}
          aria-label={`Confirmar la recogida a las ${formatearHora(propuesta, ahora)} de la reserva ${viaje.id}`}
          onClick={() => void resolver(true)}
        >
          Confirmar
        </button>
        <button
          type="button"
          className={estilos.botonSecundario}
          disabled={decidir.isPending}
          aria-label={`Descartar la propuesta de la reserva ${viaje.id}`}
          onClick={() => void resolver(false)}
        >
          Descartar
        </button>
      </span>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
    </>
  );
}

function Celda({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return <td data-titulo={titulo}>{children}</td>;
}
