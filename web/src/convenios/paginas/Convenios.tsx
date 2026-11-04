import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import campos from '../../formularios/formularios.module.css';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../../flota/componentes/comunes';
import { useFiltrosUrl } from '../../flota/filtrosUrl';
import { useConvenios, type ConsultaConvenios } from '../api';

const numero = new Intl.NumberFormat('es-CL');

/** HU-11: convenios con su volumen de reservas. */
export function Convenios() {
  const filtros = useFiltrosUrl(['activo'] as const);
  const { activo } = filtros.valores;
  const consulta: ConsultaConvenios = {
    ...(filtros.q && { q: filtros.q }),
    ...(activo && { activo: activo === 'true' }),
    ...(filtros.pagina > 1 && { page: filtros.pagina }),
  };
  const lista = useConvenios(consulta);
  const conFiltros = Boolean(filtros.q || activo);

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Convenios</h1>
        <Link to="/convenios/nuevo" className={estilos.boton}>
          Nuevo convenio
        </Link>
      </div>

      <div className={estilos.filtros}>
        <div className={estilos.camposFiltro} data-abierto="true">
          <label className={`${campos.campo} ${estilos.busqueda}`}>
            Buscar
            <input type="search" placeholder="Cliente o RUT" value={filtros.busqueda} onChange={(evento) => filtros.setBusqueda(evento.target.value)} />
          </label>
          <label className={campos.campo}>
            Estado
            <select value={activo} onChange={(evento) => filtros.cambiar({ activo: evento.target.value })}>
              <option value="">Todos</option>
              <option value="true">Activos</option>
              <option value="false">Inactivos</option>
            </select>
          </label>
        </div>
      </div>

      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando convenios" columnas={4} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="la página" reintentar={() => void lista.refetch()} />
      ) : lista.data.results.length === 0 ? (
        <div className={estilos.vacio}>
          {conFiltros ? (
            <>
              <p>Ningún convenio coincide con los filtros.</p>
              <button type="button" className={estilos.botonSecundario} onClick={() => filtros.cambiar({ q: '', activo: '' })}>
                Quitar filtros
              </button>
            </>
          ) : (
            <>
              <p>Aún no hay convenios.</p>
              <Link to="/convenios/nuevo" className={estilos.boton}>
                Nuevo convenio
              </Link>
            </>
          )}
        </div>
      ) : (
        <>
          <p className={estilos.resumen} aria-live="polite">
            <span>
              {numero.format(lista.data.count)} {lista.data.count === 1 ? 'convenio' : 'convenios'}
            </span>
            {lista.isFetching && <span>Actualizando…</span>}
          </p>
          <table className={estilos.tabla} aria-busy={lista.isPlaceholderData || undefined}>
            <thead>
              <tr>
                <th scope="col">Cliente</th>
                <th scope="col">RUT</th>
                <th scope="col">Reservas</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {lista.data.results.map((convenio) => (
                <tr key={convenio.id}>
                  <Celda titulo="Cliente">
                    <Link to={`/convenios/${convenio.id}`}>{convenio.cliente_nombre}</Link>
                  </Celda>
                  <Celda titulo="RUT">{convenio.cliente_rut}</Celda>
                  <Celda titulo="Reservas">{numero.format(convenio.reservas)}</Celda>
                  <Celda titulo="Estado">{convenio.activo ? 'Activo' : 'Inactivo'}</Celda>
                </tr>
              ))}
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
