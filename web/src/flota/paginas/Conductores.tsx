import { useState } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import type { NombreIcono } from '../../diseno/iconos';
import { formatearFecha, hoy } from '../../hora/hora';
import { useConductores, type ConsultaConductores, type EstadoConductor } from '../api';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../componentes/comunes';
import { useEstadoEnVivo } from '../estadoEnVivo';
import { ACCESOS_APP, avisoLicencia, ESTADOS_CONDUCTOR } from '../etiquetas';
import { useFiltrosUrl } from '../filtrosUrl';
import s from '../flota.module.css';

const numero = new Intl.NumberFormat('es-CL');

type Tono = 'ok' | 'info' | 'revision' | 'peligro' | 'neutro';

/** HU-74: estilo semántico diferenciado de la insignia de acceso a la app. */
const ESTILO_ACCESO: Record<keyof typeof ACCESOS_APP, { tono: Tono; icono: NombreIcono }> = {
  ACTIVA: { tono: 'ok', icono: 'llave' },
  TEMPORAL: { tono: 'revision', icono: 'reloj' },
  TEMPORAL_VENCIDA: { tono: 'peligro', icono: 'alerta' },
  SIN_PASSWORD: { tono: 'peligro', icono: 'candado' },
  DESHABILITADA: { tono: 'neutro', icono: 'cerrar' },
};

const ESTILO_ESTADO: Record<EstadoConductor, { tono: Tono; icono: NombreIcono }> = {
  DISPONIBLE: { tono: 'ok', icono: 'check' },
  EN_VIAJE: { tono: 'info', icono: 'auto' },
  NO_DISPONIBLE: { tono: 'neutro', icono: 'menos' },
};

export function Conductores() {
  const filtros = useFiltrosUrl(['estado', 'activo'] as const);
  const { estado, activo } = filtros.valores;
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const consulta: ConsultaConductores = {
    ...(filtros.q && { q: filtros.q }),
    ...(estado in ESTADOS_CONDUCTOR && { estado: estado as EstadoConductor }),
    ...(activo && { activo: activo === 'true' }),
    ...(filtros.pagina > 1 && { page: filtros.pagina }),
  };
  const lista = useConductores(consulta);
  const enVivo = useEstadoEnVivo();
  const fechaHoy = hoy();
  const conFiltros = Boolean(filtros.q || estado || activo);
  const activos = (filtros.q ? 1 : 0) + (estado ? 1 : 0) + (activo ? 1 : 0);

  return (
    <section>
      <div className={s.encabezado}>
        <div className={s.tituloBloque}>
          <div className={s.metaFicha}>
            <h1>Conductores</h1>
            {enVivo === 'conectado' && (
              <span className={s.indicadorVivo}>
                <span className={s.puntoVivo} aria-hidden="true" />
                En vivo
              </span>
            )}
          </div>
          <p className={s.subtitulo}>Supervisa turnos, licencias, vehículos asociados y acceso a la app del conductor.</p>
        </div>
        <div className={s.accionesEncabezado}>
          <Link to="/conductores/importar" className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
            <Icono nombre="lista" tamano={16} />
            Cargar CSV
          </Link>
          <Link to="/conductores/nuevo" className={`${estilos.boton} ${s.botonConIcono}`}>
            <Icono nombre="mas" tamano={16} />
            Nuevo conductor
          </Link>
        </div>
      </div>

      {enVivo === 'reconectando' && (
        <Aviso tipo="error">Sin conexión en vivo: el estado puede estar desactualizado. Reconectando…</Aviso>
      )}

      <div className={s.filtros}>
        <button
          type="button"
          className={s.botonFiltros}
          aria-expanded={filtrosAbiertos}
          aria-controls="campos-filtro-conductores"
          onClick={() => setFiltrosAbiertos((abiertos) => !abiertos)}
        >
          <span>Filtros{activos ? ` (${activos})` : ''}</span>
          <Icono nombre="abajo" tamano={16} />
        </button>

        <div id="campos-filtro-conductores" className={s.camposFiltro} data-abierto={filtrosAbiertos} role="search">
          <div className={s.filaFiltrosConductores}>
            <label className={s.campoFiltro}>
              Buscar
              <input
                type="search"
                className={s.control}
                placeholder="Nombre, RUT, correo o patente"
                value={filtros.busqueda}
                onChange={(evento) => filtros.setBusqueda(evento.target.value)}
              />
            </label>
            <label className={s.campoFiltro}>
              Estado
              <select className={s.control} value={estado} onChange={(evento) => filtros.cambiar({ estado: evento.target.value })}>
                <option value="">Todos</option>
                {Object.entries(ESTADOS_CONDUCTOR).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </label>
            <label className={s.campoFiltro}>
              Cuenta
              <select className={s.control} value={activo} onChange={(evento) => filtros.cambiar({ activo: evento.target.value })}>
                <option value="">Todas</option>
                <option value="true">Habilitadas</option>
                <option value="false">Deshabilitadas</option>
              </select>
            </label>
            {conFiltros && (
              <button type="button" className={s.botonLimpiar} onClick={() => filtros.cambiar({ q: '', estado: '', activo: '' })}>
                <Icono nombre="cerrar" tamano={15} />
                Limpiar
              </button>
            )}
          </div>
        </div>
      </div>

      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando conductores" columnas={7} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="la página" reintentar={() => void lista.refetch()} />
      ) : lista.data.results.length === 0 ? (
        <div className={s.vacio}>
          <div className={s.iconoVacio} aria-hidden="true">
            <Icono nombre="volante" tamano={24} />
          </div>
          <p>{conFiltros ? 'Ningún conductor coincide con los filtros.' : 'Aún no hay conductores.'}</p>
          {conFiltros ? (
            <button type="button" className={estilos.botonSecundario} onClick={() => filtros.cambiar({ q: '', estado: '', activo: '' })}>
              Quitar filtros
            </button>
          ) : (
            <div className={s.accionesVacio}>
              <Link to="/conductores/nuevo" className={`${estilos.boton} ${s.botonConIcono}`}>
                <Icono nombre="mas" tamano={16} />
                Nuevo conductor
              </Link>
              <Link to="/conductores/importar" className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
                <Icono nombre="lista" tamano={16} />
                Cargar CSV
              </Link>
            </div>
          )}
        </div>
      ) : (
        <>
          <p className={estilos.resumen} aria-live="polite">
            <span>
              {numero.format(lista.data.count)} {lista.data.count === 1 ? 'conductor' : 'conductores'}
            </span>
            {lista.isFetching && <span>Actualizando…</span>}
          </p>
          <div className={s.contenedorTabla}>
            <table className={s.tablaFlota} aria-busy={lista.isPlaceholderData || undefined}>
              <thead>
                <tr>
                  <th scope="col">Nombre</th>
                  <th scope="col">Contacto</th>
                  <th scope="col">Licencia</th>
                  <th scope="col">Vehículos</th>
                  <th scope="col">Estado</th>
                  <th scope="col">Acceso a la app</th>
                  <th scope="col" className={s.colAccion}>
                    <span className="solo-lector">Acción</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.data.results.map((conductor) => {
                  const aviso = avisoLicencia(conductor.licencia_vence, fechaHoy);
                  const claveAcceso = conductor.activo ? conductor.acceso : 'DESHABILITADA';
                  const estiloEstado = ESTILO_ESTADO[conductor.estado];
                  const estiloAcceso = ESTILO_ACCESO[claveAcceso];
                  return (
                    <tr key={conductor.id}>
                      <Celda titulo="Nombre">
                        <Link to={`/conductores/${conductor.id}`} className={s.enlacePrincipal}>
                          {conductor.nombre}
                        </Link>
                        <span className={s.secundario}>{conductor.rut}</span>
                      </Celda>
                      <Celda titulo="Contacto">
                        <span className={s.tabular}>{conductor.telefono}</span>
                        <span className={s.secundario}>{conductor.email}</span>
                      </Celda>
                      <Celda titulo="Licencia">
                        <span>
                          {conductor.licencia_clase} · vence {formatearFecha(conductor.licencia_vence)}
                        </span>
                        {aviso && (
                          <div>
                            <span className={s.badgeLicencia} data-tono={aviso === 'Licencia vencida' ? 'peligro' : 'revision'}>
                              <Icono nombre="alerta" tamano={12} />
                              {aviso}
                            </span>
                          </div>
                        )}
                      </Celda>
                      <Celda titulo="Vehículos">
                        {conductor.vehiculos.length ? (
                          <div className={s.listaChips}>
                            {conductor.vehiculos.map((v) => (
                              <Link key={v.id} to={`/vehiculos/${v.id}`} className={s.patente}>
                                {v.patente}
                              </Link>
                            ))}
                          </div>
                        ) : (
                          '—'
                        )}
                      </Celda>
                      <Celda titulo="Estado">
                        <span className={s.badge} data-tono={estiloEstado.tono}>
                          <Icono nombre={estiloEstado.icono} tamano={13} />
                          {ESTADOS_CONDUCTOR[conductor.estado]}
                        </span>
                      </Celda>
                      <Celda titulo="Acceso a la app">
                        <span className={s.badge} data-tono={estiloAcceso.tono}>
                          <Icono nombre={estiloAcceso.icono} tamano={13} />
                          {ACCESOS_APP[claveAcceso]}
                        </span>
                      </Celda>
                      <Celda titulo="Acción" className={s.colAccion}>
                        <Link to={`/conductores/${conductor.id}`} className={s.enlaceDetalle}>
                          Ver ficha
                        </Link>
                      </Celda>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Paginacion
            anterior={Boolean(lista.data.previous)}
            siguiente={Boolean(lista.data.next)}
            pagina={filtros.pagina}
            ir={(pagina) => filtros.cambiar({ page: String(pagina) })}
          />
        </>
      )}
    </section>
  );
}
