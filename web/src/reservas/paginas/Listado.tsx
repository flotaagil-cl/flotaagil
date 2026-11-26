import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { Link, useSearchParams } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { esDiaFuturo, formatearFecha, formatearFechaHora, formatearPared, hoy } from '../../hora/hora';
import { LineaVuelo } from '../../vuelos/LineaVuelo';
import { lineaDeVuelo } from '../../vuelos/textos';
import { useAhora } from '../../vuelos/useAhora';
import cv from '../../vuelos/vuelos.module.css';
import { useViajes, type Canal, type EstadoViaje, type Sentido, type Viaje } from '../api';
import { DialogoAsignar } from '../componentes/DialogoAsignar';
import { EstadoEtiqueta } from '../componentes/EstadoEtiqueta';
import { mensajeDeErrorApi } from '../errores';
import { ALERTAS_VUELO, CANALES, ESTADOS, ORDEN_ESTADOS, ORDENES, SENTIDOS, type Orden } from '../etiquetas';
import {
  cambiarFiltros,
  consultaDeFiltros,
  escribirFiltros,
  hayFiltros,
  leerFiltros,
  POR_PAGINA,
  SIN_FILTROS,
  type Filtros,
} from '../filtros';
import s from './Listado.module.css';

const ESPERA_BUSQUEDA_MS = 300;
const COLUMNAS_TABLA = 8;
const numero = new Intl.NumberFormat('es-CL');

interface Chip {
  clave: string;
  texto: string;
  error?: string;
  quitar: Partial<Filtros>;
}

function chipsDe(f: Filtros, errores: { desde?: string; hasta?: string }): Chip[] {
  const chips: Chip[] = [];
  if (f.desdeHoy) chips.push({ clave: 'desdeHoy', texto: 'Desde hoy 00:00', quitar: { desdeHoy: false } });
  if (f.desde) {
    chips.push({ clave: 'desde', texto: `Desde ${formatearPared(f.desde)}`, error: errores.desde, quitar: { desde: null } });
  }
  if (f.hasta) {
    chips.push({ clave: 'hasta', texto: `Hasta ${formatearPared(f.hasta)}`, error: errores.hasta, quitar: { hasta: null } });
  }
  if (f.fecha) chips.push({ clave: 'fecha', texto: `Día ${formatearFecha(f.fecha)}`, quitar: { fecha: null } });
  for (const estado of f.estado) {
    chips.push({ clave: `estado-${estado}`, texto: ESTADOS[estado], quitar: { estado: f.estado.filter((e) => e !== estado) } });
  }
  if (f.sentido) chips.push({ clave: 'sentido', texto: SENTIDOS[f.sentido], quitar: { sentido: null } });
  if (f.canal) chips.push({ clave: 'canal', texto: `Canal: ${CANALES[f.canal]}`, quitar: { canal: null } });
  if (f.sinConfirmar) chips.push({ clave: 'sin_confirmar', texto: 'Sin confirmar', quitar: { sinConfirmar: false } });
  if (f.q.trim()) chips.push({ clave: 'q', texto: `«${f.q.trim()}»`, quitar: { q: '' } });
  return chips;
}

export function Listado() {
  const [parametros, setParametros] = useSearchParams();
  const filtros = useMemo(() => leerFiltros(parametros), [parametros]);
  // «hoy» se fija al cargar la pantalla (y al cambiar los filtros), no en cada render.
  const { consulta, errores } = useMemo(() => consultaDeFiltros(filtros), [filtros]);
  const lista = useViajes(consulta);
  const ahora = useAhora();
  const refEstados = useRef<HTMLDetailsElement>(null);
  const [viajeAAsignar, setViajeAAsignar] = useState<Viaje | null>(null);
  const [avisoAsignacion, setAvisoAsignacion] = useState<string | null>(null);

  function aplicar(cambios: Partial<Filtros>, opciones: { replace?: boolean } = {}) {
    setParametros(escribirFiltros(cambiarFiltros(filtros, cambios)), opciones);
  }

  // Búsqueda: se escribe en la URL tras 300 ms sin teclear, reemplazando la entrada del historial.
  const [busqueda, setBusqueda] = useState(filtros.q);
  const [busquedaEnUrl, setBusquedaEnUrl] = useState(filtros.q);
  if (filtros.q !== busquedaEnUrl) {
    // La URL cambió desde afuera (atrás/adelante, quitar filtro): el campo la sigue.
    setBusquedaEnUrl(filtros.q);
    setBusqueda(filtros.q);
  }
  useEffect(() => {
    if (busqueda === filtros.q) return;
    const temporizador = setTimeout(() => {
      setParametros(escribirFiltros(cambiarFiltros(filtros, { q: busqueda })), { replace: true });
    }, ESPERA_BUSQUEDA_MS);
    return () => clearTimeout(temporizador);
  }, [busqueda, filtros, setParametros]);

  // Cierra el desplegable multiselect «Estado» al hacer clic fuera o presionar Escape.
  useEffect(() => {
    function cerrarAlHacerClicFuera(evento: MouseEvent) {
      const detalle = refEstados.current;
      if (!detalle?.open) return;
      if (evento.target instanceof Node && !detalle.contains(evento.target)) {
        detalle.open = false;
      }
    }
    function cerrarConEscape(evento: KeyboardEvent) {
      const detalle = refEstados.current;
      if (evento.key === 'Escape' && detalle?.open) {
        detalle.open = false;
      }
    }
    document.addEventListener('mousedown', cerrarAlHacerClicFuera);
    document.addEventListener('keydown', cerrarConEscape);
    return () => {
      document.removeEventListener('mousedown', cerrarAlHacerClicFuera);
      document.removeEventListener('keydown', cerrarConEscape);
    };
  }, []);

  // En celular los filtros quedan plegados; en escritorio siempre a la vista (CSS).
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  // El rango de fechas (fila 3) parte colapsado salvo que ya venga filtrado en la URL.
  const [fechasAbiertas, setFechasAbiertas] = useState(() => Boolean(filtros.fecha || filtros.desde || filtros.hasta));
  const chips = chipsDe(filtros, errores);
  const conFiltrosActivos = hayFiltros(filtros);
  const hoyLocal = hoy();
  const esVistaTodas =
    filtros.desdeHoy && filtros.estado.length === 0 && !filtros.sinConfirmar && !filtros.fecha && !filtros.desde && !filtros.hasta;
  const esVistaPorAsignarHoy =
    filtros.estado.length === 1 &&
    filtros.estado[0] === 'SOLICITADO' &&
    filtros.fecha === hoyLocal &&
    !filtros.sinConfirmar;
  const ESTADOS_EN_CURSO: EstadoViaje[] = ['ASIGNADO', 'ACEPTADO', 'EN_CAMINO', 'EN_ZONA', 'PASAJERO_A_BORDO'];
  const esVistaEnCurso =
    filtros.estado.length === ESTADOS_EN_CURSO.length &&
    ESTADOS_EN_CURSO.every((e) => filtros.estado.includes(e)) &&
    !filtros.sinConfirmar;
  const esVistaSinConfirmar = filtros.sinConfirmar && filtros.estado.length === 0;
  const datos = lista.data;
  const paginas = datos ? Math.max(1, Math.ceil(datos.count / POR_PAGINA)) : 1;
  const paginaInexistente = lista.error instanceof ErrorApi && lista.error.estado === 404 && filtros.pagina > 1;

  function limpiarFiltros() {
    aplicar({ ...SIN_FILTROS, ordenar: filtros.ordenar });
  }

  return (
    <section>
      <div className={s.encabezado}>
        <h1>Reservas</h1>
        <div className={s.accionesEncabezado}>
          <Link to="/reservas/contingencia" className={estilos.botonSecundario}>
            Reserva de contingencia
          </Link>
          <Link to="/reservas/nueva" className={`${estilos.boton} ${s.botonConIcono}`}>
            <Icono nombre="mas" tamano={18} />
            Nueva reserva
          </Link>
        </div>
      </div>

      {avisoAsignacion && <Aviso>{avisoAsignacion}</Aviso>}

      <div className={s.filtros}>
        <button
          type="button"
          className={s.botonFiltros}
          aria-expanded={filtrosAbiertos}
          aria-controls="campos-filtro"
          onClick={() => setFiltrosAbiertos((abiertos) => !abiertos)}
        >
          <span>Filtros{chips.length ? ` (${chips.length})` : ''}</span>
          <Icono nombre="abajo" tamano={16} />
        </button>

        <div id="campos-filtro" className={s.camposFiltro} data-abierto={filtrosAbiertos} role="search">
          <div className={s.atajosBarra}>
            <div className={s.atajosRapidos} role="group" aria-label="Vistas rápidas">
              <button
                type="button"
                className={s.atajo}
                aria-pressed={esVistaTodas}
                onClick={() =>
                  aplicar({ estado: [], sinConfirmar: false, fecha: null, desde: null, hasta: null, desdeHoy: true })
                }
              >
                Todas desde hoy
              </button>
              <button
                type="button"
                className={s.atajo}
                aria-pressed={esVistaPorAsignarHoy}
                onClick={() =>
                  aplicar({ estado: ['SOLICITADO'], fecha: hoyLocal, desde: null, hasta: null, sinConfirmar: false, desdeHoy: false })
                }
              >
                Por asignar hoy
              </button>
              <button
                type="button"
                className={s.atajo}
                aria-pressed={esVistaEnCurso}
                onClick={() =>
                  aplicar({
                    estado: ESTADOS_EN_CURSO,
                    sinConfirmar: false,
                    fecha: null,
                    desde: null,
                    hasta: null,
                    desdeHoy: true,
                  })
                }
              >
                En curso
              </button>
              <button
                type="button"
                className={s.atajo}
                aria-pressed={esVistaSinConfirmar}
                onClick={() =>
                  aplicar({ sinConfirmar: true, estado: [], fecha: null, desde: null, hasta: null, desdeHoy: false })
                }
              >
                Sin confirmar
              </button>
            </div>
            <div className={s.atajosSecundarios}>
              <button
                type="button"
                className={s.botonFechas}
                aria-expanded={fechasAbiertas}
                aria-controls="filtro-fechas"
                onClick={() => setFechasAbiertas((abierto) => !abierto)}
              >
                <Icono nombre="calendario" tamano={14} />
                <span>Fechas</span>
                <Icono nombre="abajo" tamano={14} className={fechasAbiertas ? s.flechaArriba : undefined} />
              </button>
              {conFiltrosActivos && (
                <button type="button" className={s.botonLimpiar} onClick={limpiarFiltros}>
                  <Icono nombre="cerrar" tamano={14} />
                  Limpiar filtros
                </button>
              )}
            </div>
          </div>

          <div className={s.fila1}>
            <label className={s.campoFiltro}>
              Buscar
              <input
                type="search"
                className={s.control}
                placeholder="Pasajero, teléfono, dirección o vuelo"
                value={busqueda}
                onChange={(evento) => setBusqueda(evento.target.value)}
              />
            </label>
            <label className={s.checkboxInline}>
              <input
                type="checkbox"
                className={s.checkbox}
                checked={filtros.sinConfirmar}
                onChange={(evento) => aplicar({ sinConfirmar: evento.target.checked })}
              />
              Solo sin confirmar
            </label>
          </div>

          <div className={s.fila2}>
            <div className={s.campoFiltro}>
              <span id="filtro-estado">Estado</span>
              <details ref={refEstados} className={s.estados}>
                <summary aria-labelledby="filtro-estado" className={s.estadoResumen}>
                  {filtros.estado.length ? `${filtros.estado.length} seleccionados` : 'Todos'}
                  <Icono nombre="abajo" tamano={16} className={s.estadoFlecha} />
                </summary>
                <div className={s.opcionesEstado} role="group" aria-labelledby="filtro-estado">
                  {ORDEN_ESTADOS.map((estado) => (
                    <label key={estado} className={s.opcionEstado}>
                      <input
                        type="checkbox"
                        className={s.checkbox}
                        checked={filtros.estado.includes(estado)}
                        onChange={(evento) =>
                          aplicar({
                            estado: evento.target.checked
                              ? [...filtros.estado, estado]
                              : filtros.estado.filter((e: EstadoViaje) => e !== estado),
                          })
                        }
                      />
                      {ESTADOS[estado]}
                    </label>
                  ))}
                </div>
              </details>
            </div>

            <label className={s.campoFiltro}>
              Sentido
              <select
                className={s.control}
                value={filtros.sentido ?? ''}
                onChange={(evento) => aplicar({ sentido: (evento.target.value || null) as Sentido | null })}
              >
                <option value="">Todos</option>
                {Object.entries(SENTIDOS).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </label>

            <label className={s.campoFiltro}>
              Canal
              <select
                className={s.control}
                value={filtros.canal ?? ''}
                onChange={(evento) => aplicar({ canal: (evento.target.value || null) as Canal | null })}
              >
                <option value="">Todos</option>
                {Object.entries(CANALES).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </label>

            <label className={s.campoFiltro}>
              Ordenar por
              <select
                className={s.control}
                value={filtros.ordenar ?? 'recogida_en'}
                onChange={(evento) => aplicar({ ordenar: evento.target.value === 'recogida_en' ? null : (evento.target.value as Orden) })}
              >
                {Object.entries(ORDENES).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {(fechasAbiertas || filtros.fecha || filtros.desde || filtros.hasta) && (
            <div id="filtro-fechas" className={s.fila3}>
              <label className={s.campoFiltro}>
                Día de recogida
                <input
                  type="date"
                  className={s.control}
                  value={filtros.fecha ?? ''}
                  onChange={(evento) => aplicar({ fecha: evento.target.value || null })}
                />
              </label>

              <label className={s.campoFiltro}>
                Desde
                <input
                  type="datetime-local"
                  className={s.control}
                  step={60}
                  value={filtros.desde ?? ''}
                  aria-invalid={errores.desde ? true : undefined}
                  onChange={(evento) => aplicar({ desde: evento.target.value || null })}
                />
              </label>

              <label className={s.campoFiltro}>
                Hasta
                <input
                  type="datetime-local"
                  className={s.control}
                  step={60}
                  value={filtros.hasta ?? ''}
                  aria-invalid={errores.hasta ? true : undefined}
                  onChange={(evento) => aplicar({ hasta: evento.target.value || null })}
                />
              </label>
            </div>
          )}
        </div>
      </div>

      {chips.length > 0 && (
        <ul className={estilos.chips} aria-label="Filtros activos">
          {chips.map((chip) => (
            <li key={chip.clave} className={estilos.chip} data-error={chip.error ? true : undefined}>
              {chip.texto}
              <button type="button" aria-label={`Quitar filtro ${chip.texto}`} onClick={() => aplicar(chip.quitar)}>
                ×
              </button>
            </li>
          ))}
          <li>
            <button type="button" className={estilos.quitarTodo} onClick={limpiarFiltros}>
              Quitar filtros
            </button>
          </li>
        </ul>
      )}
      {[errores.desde, errores.hasta].filter(Boolean).map((mensaje) => (
        <Aviso key={mensaje} tipo="error">
          {mensaje} El filtro no se aplicó.
        </Aviso>
      ))}

      {lista.isPending ? (
        <Esqueleto />
      ) : paginaInexistente ? (
        <div className={estilos.vacio}>
          <p>Esa página no existe.</p>
          <button type="button" className={estilos.botonSecundario} onClick={() => aplicar({ pagina: 1 })}>
            Ir a la primera página
          </button>
        </div>
      ) : lista.isError ? (
        <div className={estilos.vacio} role="alert">
          <p>{mensajeDeErrorApi(lista.error)}</p>
          <button type="button" className={estilos.boton} onClick={() => void lista.refetch()}>
            Reintentar
          </button>
        </div>
      ) : datos && datos.results.length === 0 ? (
        <div className={estilos.vacio}>
          {conFiltrosActivos ? (
            <>
              <p>Ninguna reserva coincide con los filtros.</p>
              <button type="button" className={estilos.botonSecundario} onClick={limpiarFiltros}>
                Quitar filtros
              </button>
            </>
          ) : (
            <>
              <p>Aún no hay reservas.</p>
              <Link to="/reservas/nueva" className={`${estilos.boton} ${s.botonConIcono}`}>
                <Icono nombre="mas" tamano={18} />
                Nueva reserva
              </Link>
            </>
          )}
        </div>
      ) : (
        datos && (
          <>
            <p className={estilos.resumen} aria-live="polite">
              <span>
                {numero.format(datos.count)} {datos.count === 1 ? 'reserva' : 'reservas'} · página {filtros.pagina} de {paginas}
              </span>
              {lista.isFetching && <span>Actualizando…</span>}
            </p>
            <div className={s.contenedorTabla}>
              <table className={s.tablaReservas} aria-busy={lista.isPlaceholderData || undefined}>
                <thead>
                  <tr>
                    <th scope="col" className={s.colId}>
                      N°
                    </th>
                    <th scope="col">Recogida</th>
                    <th scope="col">Pasajero</th>
                    <th scope="col">Trayecto</th>
                    <th scope="col">Sentido / Canal</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Conductor / Vehículo</th>
                    <th scope="col" className={s.colAccion}>
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {datos.results.map((viaje) => {
                    // HU-69: la línea de vuelo va en su propia fila, pegada a la de la reserva.
                    const linea = lineaDeVuelo(viaje, ahora);
                    const estado = viaje.estado ?? 'SOLICITADO';
                    const urgencia =
                      viaje.alerta_vuelo || viaje.sin_confirmar
                        ? 'alerta'
                        : estado === 'SOLICITADO' && !esDiaFuturo(viaje.recogida_en)
                          ? 'asignar'
                          : undefined;
                    return (
                      <Fragment key={viaje.id}>
                        <tr data-con-vuelo={linea ? 'true' : undefined} data-urgencia={urgencia}>
                          <Celda titulo="N°" clase={s.colId}>
                            <strong className={s.numeroId}>#{viaje.id}</strong>
                          </Celda>
                          <Celda titulo="Recogida" clase={s.colRecogida}>
                            <Link to={`/reservas/${viaje.id}`} className={s.enlaceRecogida}>
                              {formatearFechaHora(viaje.recogida_en)}
                            </Link>
                          </Celda>
                          <Celda titulo="Pasajero">
                            <span className={s.pasajeroNombre}>{viaje.pasajero.nombre}</span>
                            <span className={estilos.secundario}>{viaje.pasajero.telefono ?? 'Sin teléfono'}</span>
                            {viaje.solicitante_nombre && <span className={estilos.secundario}>Solicitado por {viaje.solicitante_nombre}</span>}
                          </Celda>
                          <Celda titulo="Trayecto" clase={s.colTrayecto}>
                            {viaje.origen.direccion}
                            <span className={estilos.secundario}>→ {viaje.destino.direccion}</span>
                            {(viaje.vuelo || viaje.convenio || viaje.grupo) && (
                              <div className={s.insigniasTrayecto}>
                                {viaje.vuelo && (
                                  <span className={s.badgeVuelo}>
                                    <Icono nombre="avion" tamano={13} />
                                    {viaje.vuelo.numero}
                                  </span>
                                )}
                                {viaje.convenio && (
                                  <span className={s.badgeConvenio}>
                                    <Icono nombre="convenios" tamano={13} />
                                    {viaje.convenio.cliente_nombre}
                                  </span>
                                )}
                                {viaje.grupo && (
                                  <Link to={`/reservas/${viaje.id}#grupo`} className={s.badgeConvenio}>
                                    <Icono nombre="auto" tamano={13} />
                                    Vehículos separados
                                  </Link>
                                )}
                              </div>
                            )}
                          </Celda>
                          <Celda titulo="Sentido / Canal" clase={s.colSentido}>
                            {viaje.sentido ? SENTIDOS[viaje.sentido] : '—'}
                            <span className={estilos.secundario}>{CANALES[viaje.canal]}</span>
                          </Celda>
                          <Celda titulo="Estado" clase={s.colEstado}>
                            <EstadoEtiqueta estado={estado} sinConfirmar={viaje.sin_confirmar} />
                            {viaje.alerta_vuelo && <span className={estilos.alerta}>{ALERTAS_VUELO[viaje.alerta_vuelo]}</span>}
                          </Celda>
                          <Celda titulo="Conductor / Vehículo">
                            {viaje.conductor || viaje.vehiculo ? (
                              <>
                                <span>{viaje.conductor?.nombre ?? 'Sin conductor'}</span>
                                {viaje.vehiculo?.patente && (
                                  <div>
                                    <span className={s.patente}>{viaje.vehiculo.patente}</span>
                                  </div>
                                )}
                              </>
                            ) : (
                              <span className={s.sinAsignar}>Sin asignar</span>
                            )}
                          </Celda>
                          <Celda titulo="Acción" clase={s.colAccion}>
                            {estado === 'SOLICITADO' ? (
                              <div className={s.accionesFila}>
                                <button
                                  type="button"
                                  className={s.botonAsignar}
                                  disabled={esDiaFuturo(viaje.recogida_en)}
                                  onClick={() => setViajeAAsignar(viaje)}
                                >
                                  Asignar
                                </button>
                                {esDiaFuturo(viaje.recogida_en) && (
                                  <span className={s.badgeFuturo}>Disponible para asignar el día del viaje</span>
                                )}
                              </div>
                            ) : (
                              <Link to={`/reservas/${viaje.id}`} className={s.enlaceDetalle}>
                                Ver detalle
                              </Link>
                            )}
                          </Celda>
                        </tr>
                        {linea && (
                          <tr className={cv.filaVuelo} aria-label={`Vuelo de la reserva ${viaje.id}`}>
                            <td colSpan={COLUMNAS_TABLA}>
                              <LineaVuelo linea={linea} />
                            </td>
                          </tr>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {paginas > 1 && (
              <nav className={estilos.paginacion} aria-label="Paginación">
                <button
                  type="button"
                  className={estilos.botonSecundario}
                  disabled={!datos.previous}
                  onClick={() => aplicar({ pagina: filtros.pagina - 1 })}
                >
                  Anterior
                </button>
                <button
                  type="button"
                  className={estilos.botonSecundario}
                  disabled={!datos.next}
                  onClick={() => aplicar({ pagina: filtros.pagina + 1 })}
                >
                  Siguiente
                </button>
              </nav>
            )}
          </>
        )
      )}

      {viajeAAsignar && (
        <DialogoAsignar
          viaje={viajeAAsignar}
          alCerrar={() => setViajeAAsignar(null)}
          alAsignar={(nombre) => {
            const idAsignado = viajeAAsignar.id;
            setViajeAAsignar(null);
            setAvisoAsignacion(`Reserva #${idAsignado} asignada a ${nombre}. Esperando que acepte en la app (60 s).`);
          }}
        />
      )}
    </section>
  );
}

/** Celda con su título: en celular la tabla pasa a tarjetas y el título va a la izquierda (CSS). */
function Celda({ titulo, clase, children }: { titulo: string; clase?: string; children: ReactNode }) {
  return (
    <td data-titulo={titulo} className={clase}>
      <div>{children}</div>
    </td>
  );
}

function Esqueleto() {
  return (
    <div className={s.contenedorTabla}>
      <table className={s.tablaReservas} aria-busy="true" aria-label="Cargando reservas">
        <tbody>
          {Array.from({ length: 5 }, (_, i) => (
            <tr key={i} className={estilos.esqueleto}>
              <td colSpan={COLUMNAS_TABLA}>
                <span />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
