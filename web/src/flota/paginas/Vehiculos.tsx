import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import campos from '../../formularios/formularios.module.css';
import { useVehiculos, type ConsultaVehiculos } from '../api';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../componentes/comunes';
import { useFiltrosUrl } from '../filtrosUrl';

const numero = new Intl.NumberFormat('es-CL');

export function Vehiculos() {
  const filtros = useFiltrosUrl(['activo'] as const);
  const { activo } = filtros.valores;
  const consulta: ConsultaVehiculos = {
    ...(filtros.q && { q: filtros.q }),
    ...(activo && { activo: activo === 'true' }),
    ...(filtros.pagina > 1 && { page: filtros.pagina }),
  };
  const lista = useVehiculos(consulta);
  const conFiltros = Boolean(filtros.q || activo);

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Vehículos</h1>
        <div className={estilos.acciones}>
          <Link to="/vehiculos/importar" className={estilos.botonSecundario}>
            Cargar CSV
          </Link>
          <Link to="/vehiculos/nuevo" className={estilos.boton}>
            Nuevo vehículo
          </Link>
        </div>
      </div>

      <div className={estilos.filtros}>
        <div className={estilos.camposFiltro} data-abierto="true">
          <label className={`${campos.campo} ${estilos.busqueda}`}>
            Buscar
            <input
              type="search"
              placeholder="Patente o marca y modelo"
              value={filtros.busqueda}
              onChange={(evento) => filtros.setBusqueda(evento.target.value)}
            />
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
        <Esqueleto etiqueta="Cargando vehículos" columnas={5} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="la página" reintentar={() => void lista.refetch()} />
      ) : lista.data.results.length === 0 ? (
        <div className={estilos.vacio}>
          {conFiltros ? (
            <>
              <p>Ningún vehículo coincide con los filtros.</p>
              <button type="button" className={estilos.botonSecundario} onClick={() => filtros.cambiar({ q: '', activo: '' })}>
                Quitar filtros
              </button>
            </>
          ) : (
            <>
              <p>Aún no hay vehículos registrados.</p>
              <Link to="/vehiculos/nuevo" className={estilos.boton}>
                Nuevo vehículo
              </Link>
              <Link to="/vehiculos/importar" className={estilos.botonSecundario}>
                Cargar CSV
              </Link>
            </>
          )}
        </div>
      ) : (
        <>
          <p className={estilos.resumen} aria-live="polite">
            <span>
              {numero.format(lista.data.count)} {lista.data.count === 1 ? 'vehículo' : 'vehículos'}
            </span>
            {lista.isFetching && <span>Actualizando…</span>}
          </p>
          <table className={estilos.tabla} aria-busy={lista.isPlaceholderData || undefined}>
            <thead>
              <tr>
                <th scope="col">Patente</th>
                <th scope="col">Marca y modelo</th>
                <th scope="col">Año · capacidad</th>
                <th scope="col">Conductores</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {lista.data.results.map((vehiculo) => (
                <tr key={vehiculo.id}>
                  <Celda titulo="Patente">
                    <Link to={`/vehiculos/${vehiculo.id}`}>{vehiculo.patente}</Link>
                  </Celda>
                  <Celda titulo="Marca y modelo">{vehiculo.marca_modelo}</Celda>
                  <Celda titulo="Año · capacidad">
                    {vehiculo.anio} · {vehiculo.capacidad} {vehiculo.capacidad === 1 ? 'pasajero' : 'pasajeros'}
                  </Celda>
                  <Celda titulo="Conductores">
                    {vehiculo.conductores.length ? vehiculo.conductores.map((c) => c.nombre).join(', ') : '—'}
                  </Celda>
                  <Celda titulo="Estado">
                    <span className={`${estilos.etiqueta} ${vehiculo.activo ? estilos.curso : estilos.cancelado}`}>
                      {vehiculo.activo ? 'Activo' : 'Inactivo'}
                    </span>
                  </Celda>
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
