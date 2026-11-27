import { useState } from 'react';
import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { useVehiculos, type ConsultaVehiculos } from '../api';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../componentes/comunes';
import { useFiltrosUrl } from '../filtrosUrl';
import s from '../flota.module.css';

const numero = new Intl.NumberFormat('es-CL');

export function Vehiculos() {
  const filtros = useFiltrosUrl(['activo'] as const);
  const { activo } = filtros.valores;
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const consulta: ConsultaVehiculos = {
    ...(filtros.q && { q: filtros.q }),
    ...(activo && { activo: activo === 'true' }),
    ...(filtros.pagina > 1 && { page: filtros.pagina }),
  };
  const lista = useVehiculos(consulta);
  const conFiltros = Boolean(filtros.q || activo);
  const activos = (filtros.q ? 1 : 0) + (activo ? 1 : 0);

  return (
    <section>
      <div className={s.encabezado}>
        <div className={s.tituloBloque}>
          <h1>Vehículos</h1>
          <p className={s.subtitulo}>Administra la flota registrada, su capacidad, color y conductores asociados.</p>
        </div>
        <div className={s.accionesEncabezado}>
          <Link to="/vehiculos/importar" className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
            <Icono nombre="lista" tamano={16} />
            Cargar CSV
          </Link>
          <Link to="/vehiculos/nuevo" className={`${estilos.boton} ${s.botonConIcono}`}>
            <Icono nombre="mas" tamano={16} />
            Nuevo vehículo
          </Link>
        </div>
      </div>

      <div className={s.filtros}>
        <button
          type="button"
          className={s.botonFiltros}
          aria-expanded={filtrosAbiertos}
          aria-controls="campos-filtro-vehiculos"
          onClick={() => setFiltrosAbiertos((abiertos) => !abiertos)}
        >
          <span>Filtros{activos ? ` (${activos})` : ''}</span>
          <Icono nombre="abajo" tamano={16} />
        </button>

        <div id="campos-filtro-vehiculos" className={s.camposFiltro} data-abierto={filtrosAbiertos} role="search">
          <div className={s.filaFiltrosVehiculos}>
            <label className={s.campoFiltro}>
              Buscar
              <input
                type="search"
                className={s.control}
                placeholder="Patente o marca y modelo"
                value={filtros.busqueda}
                onChange={(evento) => filtros.setBusqueda(evento.target.value)}
              />
            </label>
            <label className={s.campoFiltro}>
              Estado
              <select className={s.control} value={activo} onChange={(evento) => filtros.cambiar({ activo: evento.target.value })}>
                <option value="">Todos</option>
                <option value="true">Activos</option>
                <option value="false">Inactivos</option>
              </select>
            </label>
            {conFiltros && (
              <button type="button" className={s.botonLimpiar} onClick={() => filtros.cambiar({ q: '', activo: '' })}>
                <Icono nombre="cerrar" tamano={15} />
                Limpiar
              </button>
            )}
          </div>
        </div>
      </div>

      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando vehículos" columnas={6} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="la página" reintentar={() => void lista.refetch()} />
      ) : lista.data.results.length === 0 ? (
        <div className={s.vacio}>
          <div className={s.iconoVacio} aria-hidden="true">
            <Icono nombre="auto" tamano={24} />
          </div>
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
              <div className={s.accionesVacio}>
                <Link to="/vehiculos/nuevo" className={`${estilos.boton} ${s.botonConIcono}`}>
                  <Icono nombre="mas" tamano={16} />
                  Nuevo vehículo
                </Link>
                <Link to="/vehiculos/importar" className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
                  <Icono nombre="lista" tamano={16} />
                  Cargar CSV
                </Link>
              </div>
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
          <div className={s.contenedorTabla}>
            <table className={s.tablaFlota} aria-busy={lista.isPlaceholderData || undefined}>
              <thead>
                <tr>
                  <th scope="col">Patente</th>
                  <th scope="col">Marca y modelo</th>
                  <th scope="col">Año · capacidad</th>
                  <th scope="col">Conductores</th>
                  <th scope="col">Estado</th>
                  <th scope="col" className={s.colAccion}>
                    <span className="solo-lector">Acción</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.data.results.map((vehiculo) => (
                  <tr key={vehiculo.id}>
                    <Celda titulo="Patente">
                      <Link to={`/vehiculos/${vehiculo.id}`} className={s.patente}>
                        {vehiculo.patente}
                      </Link>
                    </Celda>
                    <Celda titulo="Marca y modelo">
                      <span>{vehiculo.marca_modelo}</span>
                      {vehiculo.color && <span className={s.secundario}>{vehiculo.color}</span>}
                    </Celda>
                    <Celda titulo="Año · capacidad" className={s.tabular}>
                      {vehiculo.anio} · {vehiculo.capacidad} {vehiculo.capacidad === 1 ? 'pasajero' : 'pasajeros'}
                    </Celda>
                    <Celda titulo="Conductores">
                      {vehiculo.conductores.length ? (
                        <div className={s.listaChips}>
                          {vehiculo.conductores.map((c) => (
                            <Link key={c.id} to={`/conductores/${c.id}`} className={s.chipEnlace}>
                              {c.nombre}
                            </Link>
                          ))}
                        </div>
                      ) : (
                        '—'
                      )}
                    </Celda>
                    <Celda titulo="Estado">
                      <span className={s.badge} data-tono={vehiculo.activo ? 'ok' : 'peligro'}>
                        <Icono nombre={vehiculo.activo ? 'check' : 'cerrar'} tamano={13} />
                        {vehiculo.activo ? 'Activo' : 'Inactivo'}
                      </span>
                    </Celda>
                    <Celda titulo="Acción" className={s.colAccion}>
                      <Link to={`/vehiculos/${vehiculo.id}`} className={s.enlaceDetalle}>
                        Ver ficha
                      </Link>
                    </Celda>
                  </tr>
                ))}
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
