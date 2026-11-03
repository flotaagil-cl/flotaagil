import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import campos from '../../formularios/formularios.module.css';
import { formatearFecha, hoy } from '../../hora/hora';
import { useConductores, type ConsultaConductores, type EstadoConductor } from '../api';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../componentes/comunes';
import { avisoLicencia, ESTADOS_CONDUCTOR } from '../etiquetas';
import { useFiltrosUrl } from '../filtrosUrl';

const numero = new Intl.NumberFormat('es-CL');
const SIN_ACCESO = {
  SIN_PASSWORD: 'Sin contraseña',
  TEMPORAL: 'Contraseña temporal',
  TEMPORAL_VENCIDA: 'Temporal vencida',
} as const;
const CLASE_ESTADO: Record<EstadoConductor, string> = {
  DISPONIBLE: estilos.curso,
  EN_VIAJE: estilos.pendiente,
  NO_DISPONIBLE: estilos.fin,
};

export function Conductores() {
  const filtros = useFiltrosUrl(['estado', 'activo'] as const);
  const { estado, activo } = filtros.valores;
  const consulta: ConsultaConductores = {
    ...(filtros.q && { q: filtros.q }),
    ...(estado in ESTADOS_CONDUCTOR && { estado: estado as EstadoConductor }),
    ...(activo && { activo: activo === 'true' }),
    ...(filtros.pagina > 1 && { page: filtros.pagina }),
  };
  const lista = useConductores(consulta);
  const fechaHoy = hoy();

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Conductores</h1>
        <div className={estilos.acciones}>
          <Link to="/conductores/importar" className={estilos.botonSecundario}>
            Cargar CSV
          </Link>
          <Link to="/conductores/nuevo" className={estilos.boton}>
            Nuevo conductor
          </Link>
        </div>
      </div>

      <div className={estilos.filtros}>
        <div className={estilos.camposFiltro} data-abierto="true">
          <label className={`${campos.campo} ${estilos.busqueda}`}>
            Buscar
            <input
              type="search"
              placeholder="Nombre, RUT, correo o patente"
              value={filtros.busqueda}
              onChange={(evento) => filtros.setBusqueda(evento.target.value)}
            />
          </label>
          <label className={campos.campo}>
            Estado
            <select value={estado} onChange={(evento) => filtros.cambiar({ estado: evento.target.value })}>
              <option value="">Todos</option>
              {Object.entries(ESTADOS_CONDUCTOR).map(([valor, texto]) => (
                <option key={valor} value={valor}>
                  {texto}
                </option>
              ))}
            </select>
          </label>
          <label className={campos.campo}>
            Cuenta
            <select value={activo} onChange={(evento) => filtros.cambiar({ activo: evento.target.value })}>
              <option value="">Todas</option>
              <option value="true">Habilitadas</option>
              <option value="false">Deshabilitadas</option>
            </select>
          </label>
        </div>
      </div>

      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando conductores" columnas={5} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="la página" reintentar={() => void lista.refetch()} />
      ) : lista.data.results.length === 0 ? (
        <div className={estilos.vacio}>
          <p>{filtros.q || estado || activo ? 'Ningún conductor coincide con los filtros.' : 'Aún no hay conductores.'}</p>
          {(filtros.q || estado || activo) && (
            <button
              type="button"
              className={estilos.botonSecundario}
              onClick={() => filtros.cambiar({ q: '', estado: '', activo: '' })}
            >
              Quitar filtros
            </button>
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
          <table className={estilos.tabla} aria-busy={lista.isPlaceholderData || undefined}>
            <thead>
              <tr>
                <th scope="col">Nombre</th>
                <th scope="col">Contacto</th>
                <th scope="col">Licencia</th>
                <th scope="col">Vehículos</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {lista.data.results.map((conductor) => {
                const aviso = avisoLicencia(conductor.licencia_vence, fechaHoy);
                return (
                  <tr key={conductor.id}>
                    <Celda titulo="Nombre">
                      <Link to={`/conductores/${conductor.id}`}>{conductor.nombre}</Link>
                      <span className={estilos.secundario}>{conductor.rut}</span>
                    </Celda>
                    <Celda titulo="Contacto">
                      {conductor.telefono}
                      <span className={estilos.secundario}>{conductor.email}</span>
                    </Celda>
                    <Celda titulo="Licencia">
                      {conductor.licencia_clase} · vence {formatearFecha(conductor.licencia_vence)}
                      {aviso && <span className={estilos.alerta}>{aviso}</span>}
                    </Celda>
                    <Celda titulo="Vehículos">
                      {conductor.vehiculos.length ? conductor.vehiculos.map((v) => v.patente).join(', ') : '—'}
                    </Celda>
                    <Celda titulo="Estado">
                      <span className={`${estilos.etiqueta} ${CLASE_ESTADO[conductor.estado]}`}>
                        {ESTADOS_CONDUCTOR[conductor.estado]}
                      </span>
                      {!conductor.activo && <span className={estilos.alerta}>Cuenta deshabilitada</span>}
                      {conductor.activo && conductor.acceso !== 'ACTIVA' && (
                        <span className={estilos.alerta}>{SIN_ACCESO[conductor.acceso]}</span>
                      )}
                    </Celda>
                  </tr>
                );
              })}
            </tbody>
          </table>
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
