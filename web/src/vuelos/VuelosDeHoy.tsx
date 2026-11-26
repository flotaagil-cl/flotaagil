/**
 * HU-69: «Vuelos de hoy» (administrador y despachador). Viajes de aeropuerto del día (o próximos días) de la
 * empresa, ordenados por la hora del vuelo, con contadores interactivos, filtros, asignación directa y propuesta de
 * recogida confirmable desde la fila (RN-02). Se actualiza sola cada minuto y permite consultar bajo demanda.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { Link } from 'react-router';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import estilos from '../componentes/panel.module.css';
import { Icono } from '../diseno/Icono';
import { Segmentado } from '../diseno/Segmentado';
import { FallaDeCarga } from '../flota/componentes/comunes';
import { esDiaFuturo, formatearFecha, formatearHora } from '../hora/hora';
import { useDecidirRecogida } from '../reservas/api';
import { ContactoPasajero } from '../reservas/componentes/ContactoPasajero';
import { DialogoAsignar } from '../reservas/componentes/DialogoAsignar';
import { mensajeDeErrorApi } from '../reservas/errores';
import { ESTADOS_VUELO } from '../reservas/etiquetas';
import { useApi } from '../sesion/SesionProvider';
import { EstadoVuelo } from './LineaVuelo';
import { cuentaRegresiva, enEspera, estadoDeVuelo, llegadaDe, minutosHasta, tipoDeSalida } from './textos';
import { useAhora } from './useAhora';
import c from './vuelos.module.css';

type Viaje = components['schemas']['Viaje'];
type EstadoVueloApi = components['schemas']['EstadoVueloEnum'];
type Tipo = 'todos' | 'llegadas' | 'salidas';
type Rango = 'hoy' | 'manana' | 'proximos_3_dias';
type FiltroRapido = 'cancelados_o_desviados' | 'sin_conductor' | 'propuestas_pendientes' | null;
type NivelContador = 'aviso' | 'peligro';

export const REFRESCO_MS = 60_000;

const RANGOS: { valor: Rango; texto: string }[] = [
  { valor: 'hoy', texto: 'Hoy' },
  { valor: 'manana', texto: 'Mañana' },
  { valor: 'proximos_3_dias', texto: 'Próximos 3 días' },
];

const TIPOS: { valor: Tipo; texto: string }[] = [
  { valor: 'todos', texto: 'Todos' },
  { valor: 'llegadas', texto: 'Llegadas' },
  { valor: 'salidas', texto: 'Salidas' },
];

const NOMBRES_FILTRO_RAPIDO: Record<Exclude<FiltroRapido, null>, string> = {
  cancelados_o_desviados: 'Cancelados o desviados',
  sin_conductor: 'Sin conductor',
  propuestas_pendientes: 'Con propuesta de recogida',
};

function cumpleFiltroRapido(viaje: Viaje, filtro: FiltroRapido): boolean {
  if (!filtro) return true;
  if (filtro === 'sin_conductor') return !viaje.conductor;
  if (filtro === 'cancelados_o_desviados') {
    return viaje.vuelo?.estado_vuelo === 'CANCELADO' || viaje.vuelo?.estado_vuelo === 'DESVIADO';
  }
  return Boolean(viaje.vuelo?.recogida_propuesta);
}

function coincideBusqueda(viaje: Viaje, consulta: string): boolean {
  const termino = consulta.trim().toLowerCase();
  if (!termino) return true;
  const campos = [
    `#${viaje.id}`,
    viaje.vuelo?.numero,
    viaje.vuelo?.origen_ciudad,
    viaje.vuelo_salida_numero,
    viaje.pasajero.nombre,
    viaje.pasajero.telefono,
    viaje.conductor?.nombre,
    viaje.vehiculo?.patente,
  ];
  return campos.some((valor) => valor?.toLowerCase().includes(termino));
}

function urgenciaDe(viaje: Viaje): 'peligro' | 'atencion' | undefined {
  const estado = viaje.vuelo?.estado_vuelo;
  if (estado === 'CANCELADO' || estado === 'DESVIADO') return 'peligro';
  if (viaje.vuelo?.recogida_propuesta || estado === 'DEMORADO') return 'atencion';
  return undefined;
}

export function VuelosDeHoy() {
  const api = useApi();
  const consultas = useQueryClient();
  const ahora = useAhora();
  const [rango, setRango] = useState<Rango>('hoy');
  const [tipo, setTipo] = useState<Tipo>('todos');
  const [estado, setEstado] = useState<EstadoVueloApi | ''>('');
  const [filtroRapido, setFiltroRapido] = useState<FiltroRapido>(null);
  const [busqueda, setBusqueda] = useState('');
  const [consultando, setConsultando] = useState(false);
  const [aviso, setAviso] = useState<{ tipo: 'info' | 'error'; texto: string } | null>(null);
  const [viajeAAsignar, setViajeAAsignar] = useState<Viaje | null>(null);

  const consulta = useQuery({
    queryKey: ['vuelos-de-hoy', rango, tipo, estado],
    queryFn: () =>
      resultado(
        api.GET('/api/vuelos-de-hoy/', {
          params: {
            query: {
              ...(rango !== 'hoy' && { rango }),
              ...(tipo !== 'todos' && { tipo }),
              ...(estado && { estado }),
            },
          },
        }),
      ),
    refetchInterval: REFRESCO_MS,
    placeholderData: (anterior) => anterior,
  });

  async function consultarAhora() {
    setConsultando(true);
    setAviso(null);
    try {
      const res = await resultado(api.POST('/api/vuelos-de-hoy/consultar/', { body: { rango } }));
      await Promise.all([
        consultas.invalidateQueries({ queryKey: ['vuelos-de-hoy'] }),
        consultas.invalidateQueries({ queryKey: ['alertas'] }),
      ]);
      const detalleSinDatos = res.sin_datos > 0 ? `, ${res.sin_datos} sin datos` : '';
      setAviso({
        tipo: 'info',
        texto: `Estados actualizados: ${res.actualizados} de ${res.consultados} vuelos consultados${detalleSinDatos}.`,
      });
    } catch (error) {
      setAviso({ tipo: 'error', texto: mensajeDeErrorApi(error) });
    } finally {
      setConsultando(false);
    }
  }

  function alCambiarTipo(nuevo: Tipo) {
    setTipo(nuevo);
    if (nuevo === 'salidas' && (filtroRapido === 'cancelados_o_desviados' || filtroRapido === 'propuestas_pendientes')) {
      setFiltroRapido(null);
    }
  }

  function alCambiarEstado(nuevo: EstadoVueloApi | '') {
    setEstado(nuevo);
    if (filtroRapido === 'cancelados_o_desviados' || filtroRapido === 'propuestas_pendientes') {
      setFiltroRapido(null);
    }
  }

  function alternarDemorados() {
    setFiltroRapido(null);
    if (estado === 'DEMORADO') {
      setEstado('');
      return;
    }
    setEstado('DEMORADO');
    if (tipo === 'salidas') setTipo('todos');
  }

  function alternarFiltroRapido(nuevo: Exclude<FiltroRapido, null>) {
    if (filtroRapido === nuevo) {
      setFiltroRapido(null);
      return;
    }
    setFiltroRapido(nuevo);
    if (nuevo !== 'sin_conductor') {
      setEstado('');
      if (tipo === 'salidas') setTipo('todos');
    }
  }

  function limpiarFiltros() {
    setRango('hoy');
    setTipo('todos');
    setEstado('');
    setFiltroRapido(null);
    setBusqueda('');
  }

  const viajesServidor = consulta.data?.viajes;
  const viajesVisibles = useMemo(() => {
    const lista = viajesServidor ?? [];
    if (!filtroRapido && !busqueda.trim()) return lista;
    return lista.filter((v) => cumpleFiltroRapido(v, filtroRapido) && coincideBusqueda(v, busqueda));
  }, [viajesServidor, filtroRapido, busqueda]);

  const hayFiltrosActivos = rango !== 'hoy' || tipo !== 'todos' || Boolean(estado) || Boolean(filtroRapido) || Boolean(busqueda.trim());
  const ultimaActualizacion =
    consulta.dataUpdatedAt > 0 ? formatearHora(new Date(consulta.dataUpdatedAt).toISOString(), ahora) : null;

  return (
    <section>
      <div className={c.encabezado}>
        <div>
          <h1>Vuelos de hoy</h1>
          <p className={c.subtitulo}>
            {consulta.data ? `${formatearFecha(consulta.data.fecha)} · ` : ''}
            Actualización automática cada minuto
            {ultimaActualizacion ? ` · Última carga ${ultimaActualizacion}` : ''}
          </p>
        </div>
        <button
          type="button"
          className={`${estilos.boton} ${c.botonConsultar}`}
          disabled={consultando}
          onClick={() => void consultarAhora()}
        >
          <Icono nombre="historial" tamano={16} aria-hidden="true" />
          {consultando ? 'Consultando…' : 'Consultar ahora'}
        </button>
      </div>

      {aviso && <Aviso tipo={aviso.tipo}>{aviso.texto}</Aviso>}

      {consulta.isPending ? (
        <Cargando />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="los vuelos de hoy" reintentar={() => void consulta.refetch()} />
      ) : (
        <>
          <ul className={c.contadores} aria-label="Resumen del día">
            <Contador
              valor={consulta.data.contadores.demorados}
              texto="demorados"
              nivel="aviso"
              activo={estado === 'DEMORADO' && !filtroRapido}
              onClick={alternarDemorados}
            />
            <Contador
              valor={consulta.data.contadores.cancelados_o_desviados}
              texto="cancelados o desviados"
              nivel="peligro"
              activo={filtroRapido === 'cancelados_o_desviados'}
              onClick={() => alternarFiltroRapido('cancelados_o_desviados')}
            />
            <Contador
              valor={consulta.data.contadores.sin_conductor}
              texto="sin conductor"
              nivel="peligro"
              activo={filtroRapido === 'sin_conductor'}
              onClick={() => alternarFiltroRapido('sin_conductor')}
            />
            <Contador
              valor={consulta.data.contadores.propuestas_pendientes}
              texto="propuestas de recogida pendientes"
              nivel="aviso"
              activo={filtroRapido === 'propuestas_pendientes'}
              onClick={() => alternarFiltroRapido('propuestas_pendientes')}
            />
          </ul>

          <div className={c.panelFiltros}>
            <div className={c.filtros}>
              <Segmentado etiqueta="Día" opciones={RANGOS} valor={rango} onCambiar={setRango} forma="pastillas" />
              <Segmentado etiqueta="Mostrar" opciones={TIPOS} valor={tipo} onCambiar={alCambiarTipo} forma="pastillas" />
              <label className={c.campoFiltro}>
                Estado del vuelo
                <select
                  className={c.control}
                  value={estado}
                  disabled={tipo === 'salidas'}
                  onChange={(e) => alCambiarEstado(e.target.value as EstadoVueloApi | '')}
                >
                  <option value="">Todos</option>
                  {Object.entries(ESTADOS_VUELO).map(([valor, texto]) => (
                    <option key={valor} value={valor}>
                      {texto}
                    </option>
                  ))}
                </select>
              </label>
              <label className={`${c.campoFiltro} ${c.campoBusqueda}`}>
                Buscar vuelo o pasajero
                <input
                  type="search"
                  className={c.control}
                  value={busqueda}
                  placeholder="Vuelo, pasajero, conductor o #reserva"
                  onChange={(e) => setBusqueda(e.target.value)}
                />
              </label>
            </div>
            {(hayFiltrosActivos || filtroRapido) && (
              <div className={c.barraActivos}>
                <span className={c.conteoVisible}>
                  Mostrando {viajesVisibles.length} de {consulta.data.viajes.length} vuelos
                  {filtroRapido ? ` · Filtro: ${NOMBRES_FILTRO_RAPIDO[filtroRapido]}` : ''}
                </span>
                <button type="button" className={estilos.quitarTodo} onClick={limpiarFiltros}>
                  Limpiar filtros
                </button>
              </div>
            )}
          </div>

          {consulta.data.viajes.length === 0 ? (
            <div className={estilos.vacio}>
              <p>{rango === 'hoy' ? 'No hay vuelos con estos filtros hoy.' : 'No hay vuelos con estos filtros para este período.'}</p>
            </div>
          ) : viajesVisibles.length === 0 ? (
            <div className={estilos.vacio}>
              <p>Ningún vuelo coincide con el filtro rápido o la búsqueda.</p>
              <button
                type="button"
                className={estilos.botonSecundario}
                onClick={() => {
                  setFiltroRapido(null);
                  setBusqueda('');
                }}
              >
                Ver todos los vuelos
              </button>
            </div>
          ) : (
            <table className={`${estilos.tabla} ${c.tablaVuelos}`} aria-label="Vuelos de hoy" aria-busy={consulta.isFetching || undefined}>
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
                {viajesVisibles.map((viaje) => (
                  <Fila
                    key={viaje.id}
                    viaje={viaje}
                    ahora={ahora}
                    mostrarFecha={rango === 'proximos_3_dias'}
                    alAsignar={setViajeAAsignar}
                  />
                ))}
              </tbody>
            </table>
          )}
        </>
      )}

      {viajeAAsignar && (
        <DialogoAsignar
          viaje={viajeAAsignar}
          alCerrar={() => setViajeAAsignar(null)}
          alAsignar={(nombre) => {
            const idAsignado = viajeAAsignar.id;
            setViajeAAsignar(null);
            void consultas.invalidateQueries({ queryKey: ['vuelos-de-hoy'] });
            setAviso({
              tipo: 'info',
              texto: `Reserva #${idAsignado} asignada a ${nombre}.`,
            });
          }}
        />
      )}
    </section>
  );
}

function Contador({
  valor,
  texto,
  nivel,
  activo,
  onClick,
}: {
  valor: number;
  texto: string;
  nivel: NivelContador;
  activo: boolean;
  onClick: () => void;
}) {
  return (
    <li className={c.contadorItem}>
      <button
        type="button"
        className={c.contador}
        data-nivel={nivel}
        data-atencion={valor > 0 || undefined}
        aria-pressed={activo}
        onClick={onClick}
      >
        <strong>{valor}</strong> <span>{texto}</span>
      </button>
    </li>
  );
}

function CeldaConductor({ viaje, alAsignar }: { viaje: Viaje; alAsignar: (v: Viaje) => void }) {
  if (viaje.conductor) {
    return (
      <>
        <span>{viaje.conductor.nombre}</span>
        {viaje.vehiculo?.patente && (
          <div>
            <span className={c.patente}>{viaje.vehiculo.patente}</span>
          </div>
        )}
      </>
    );
  }

  const esFuturo = esDiaFuturo(viaje.recogida_en);
  return (
    <div className={c.conductorPendiente}>
      <span className={c.sinAsignar}>Sin asignar</span>
      {viaje.estado === 'SOLICITADO' && (
        <>
          <button
            type="button"
            className={c.botonAsignar}
            disabled={esFuturo}
            aria-label={`Asignar conductor a la reserva ${viaje.id}`}
            onClick={() => alAsignar(viaje)}
          >
            Asignar
          </button>
          {esFuturo && <span className={c.notaFuturo}>Disponible el día del viaje</span>}
        </>
      )}
    </div>
  );
}

function Fila({
  viaje,
  ahora,
  mostrarFecha,
  alAsignar,
}: {
  viaje: Viaje;
  ahora: number;
  mostrarFecha: boolean;
  alAsignar: (v: Viaje) => void;
}) {
  const vuelo = viaje.vuelo;
  const detalle = `/reservas/${viaje.id}`;
  const urgencia = urgenciaDe(viaje);

  if (vuelo) {
    const llegada = llegadaDe(vuelo);
    const regresiva =
      vuelo.estado_vuelo === 'ATERRIZADO'
        ? `aterrizó ${cuentaRegresiva(llegada, Math.max(ahora, Date.parse(llegada)))}`
        : enEspera(vuelo) && minutosHasta(llegada, ahora) > 0
          ? `aterriza ${cuentaRegresiva(llegada, ahora)}`
          : '—';
    return (
      <tr data-urgencia={urgencia}>
        <Celda titulo="Vuelo">
          <div className={c.vueloPrincipal}>
            <Icono nombre="aterrizaje" tamano={15} className={c.icono} aria-hidden="true" />
            <Link to={detalle}>{vuelo.numero}</Link>
          </div>
          <span className={estilos.secundario}>
            Llegada · reserva #{viaje.id}
            {vuelo.origen_ciudad ? ` · ${vuelo.origen_ciudad}` : ''}
            {mostrarFecha ? ` · ${formatearFecha(vuelo.fecha)}` : ''}
          </span>
        </Celda>
        <Celda titulo="Programada">{formatearHora(vuelo.hora_programada, ahora)}</Celda>
        <Celda titulo="Estimada">{vuelo.hora_estimada ? formatearHora(vuelo.hora_estimada, ahora) : '—'}</Celda>
        <Celda titulo="Estado">
          <EstadoVuelo estado={estadoDeVuelo(vuelo, ahora)} />
        </Celda>
        <Celda titulo="Cuenta regresiva">{regresiva}</Celda>
        <Celda titulo="Pasajero">
          <span className={c.pasajeroNombre}>{viaje.pasajero.nombre}</span>
          <div className={c.contactoCompacto}>
            <ContactoPasajero telefono={viaje.pasajero.telefono} compacto nombre={viaje.pasajero.nombre} />
          </div>
        </Celda>
        <Celda titulo="Conductor">
          <CeldaConductor viaje={viaje} alAsignar={alAsignar} />
        </Celda>
        <Celda titulo="Recogida">
          {vuelo.recogida_propuesta ? (
            <PropuestaEnFila viaje={viaje} propuesta={vuelo.recogida_propuesta} ahora={ahora} />
          ) : (
            formatearHora(viaje.recogida_en, ahora)
          )}
        </Celda>
      </tr>
    );
  }

  const despegue = viaje.vuelo_salida_en ?? viaje.recogida_en;
  return (
    <tr data-urgencia={urgencia}>
      <Celda titulo="Vuelo">
        <div className={c.vueloPrincipal}>
          <Icono nombre="despegue" tamano={15} className={c.icono} aria-hidden="true" />
          <Link to={detalle}>
            {viaje.vuelo_salida_numero ? `Salida ${viaje.vuelo_salida_numero}` : 'Salida'}
            {tipoDeSalida(viaje)}
          </Link>
        </div>
        <span className={estilos.secundario}>
          Reserva #{viaje.id}
          {mostrarFecha ? ` · ${formatearFecha(despegue)}` : ''}
        </span>
      </Celda>
      <Celda titulo="Programada">{formatearHora(despegue, ahora)}</Celda>
      <Celda titulo="Estimada">—</Celda>
      <Celda titulo="Estado">
        <span className={estilos.secundario}>No se monitorea</span>
      </Celda>
      <Celda titulo="Cuenta regresiva">{minutosHasta(despegue, ahora) > 0 ? `despega ${cuentaRegresiva(despegue, ahora)}` : '—'}</Celda>
      <Celda titulo="Pasajero">
        <span className={c.pasajeroNombre}>{viaje.pasajero.nombre}</span>
        <div className={c.contactoCompacto}>
          <ContactoPasajero telefono={viaje.pasajero.telefono} compacto nombre={viaje.pasajero.nombre} />
        </div>
      </Celda>
      <Celda titulo="Conductor">
        <CeldaConductor viaje={viaje} alAsignar={alAsignar} />
      </Celda>
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
      await Promise.all([
        consultas.invalidateQueries({ queryKey: ['vuelos-de-hoy'] }),
        consultas.invalidateQueries({ queryKey: ['alertas'] }),
      ]);
    }
  }

  return (
    <>
      <span className={c.horaActual}>{formatearHora(viaje.recogida_en, ahora)}</span>
      <div className={c.cajaPropuesta}>
        <span className={c.aviso}>⚠ propuesta {formatearHora(propuesta, ahora)} sin confirmar</span>
        <div className={c.botonesFila}>
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
        </div>
      </div>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
    </>
  );
}

function Celda({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return <td data-titulo={titulo}>{children}</td>;
}
