import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { useEntorno } from '../../entornoContexto';
import { Esqueleto, FallaDeCarga, Paginacion } from '../../flota/componentes/comunes';
import { useFiltrosUrl } from '../../flota/filtrosUrl';
import { useSesion } from '../../sesion/SesionProvider';
import { useConvenios, type ConsultaConvenios } from '../api';
import { BadgeEstado } from '../componentes';
import s from '../convenios.module.css';
import { ESTADOS_CONVENIO } from '../estados';

const numero = new Intl.NumberFormat('es-CL');
const DURACION_FEEDBACK_MS = 2500;

function urlRegistroConvenio(origen: string, empresa: { slug: string; modulo_cuentas?: boolean }): string {
  const ruta = empresa.modulo_cuentas ? `/solicitar/${empresa.slug}/registro-empresa` : `/solicitar/${empresa.slug}/convenio`;
  return `${origen}${ruta}`;
}

/** HU-11: convenios con su volumen de reservas. */
export function Convenios() {
  const { estado: sesion } = useSesion();
  const entorno = useEntorno();
  const filtros = useFiltrosUrl(['estado'] as const);
  const { estado } = filtros.valores;
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const [estadoCopia, setEstadoCopia] = useState<'inactivo' | 'copiado' | 'error'>('inactivo');
  const temporizador = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (temporizador.current) clearTimeout(temporizador.current);
    },
    [],
  );

  const empresa = sesion.fase === 'autenticada' ? sesion.usuario.empresa : null;
  const urlRegistro = empresa ? urlRegistroConvenio(entorno.origen, empresa) : null;
  const textoWhatsapp =
    empresa && urlRegistro
      ? `Hola, puedes registrar tu empresa en convenio con ${empresa.razon_social} en el siguiente enlace: ${urlRegistro}`
      : null;
  const urlWhatsapp = textoWhatsapp ? `https://wa.me/?text=${encodeURIComponent(textoWhatsapp)}` : null;

  async function copiarEnlace() {
    if (!urlRegistro) return;
    try {
      await navigator.clipboard.writeText(urlRegistro);
      setEstadoCopia('copiado');
    } catch {
      setEstadoCopia('error');
    }
    if (temporizador.current) clearTimeout(temporizador.current);
    temporizador.current = setTimeout(() => setEstadoCopia('inactivo'), DURACION_FEEDBACK_MS);
  }

  const consulta: ConsultaConvenios = {
    ...(filtros.q && { q: filtros.q }),
    ...(estado && { estado: estado as NonNullable<ConsultaConvenios['estado']> }),
    ...(filtros.pagina > 1 && { page: filtros.pagina }),
  };
  const lista = useConvenios(consulta);
  const conFiltros = Boolean(filtros.q || estado);
  const activos = (filtros.q ? 1 : 0) + (estado ? 1 : 0);

  return (
    <section>
      <div className={s.encabezado}>
        <div className={s.tituloBloque}>
          <h1>Convenios</h1>
          <p className={s.subtitulo}>Las empresas cliente se registran en el portal y quedan en revisión hasta que las apruebes.</p>
        </div>
        {urlRegistro && urlWhatsapp && (
          <div className={s.accionesEncabezado}>
            <button
              type="button"
              className={`${estilos.botonSecundario} ${s.botonConIcono}`}
              data-copiado={estadoCopia === 'inactivo' ? undefined : estadoCopia}
              aria-live="polite"
              onClick={() => void copiarEnlace()}
            >
              <Icono nombre={estadoCopia === 'copiado' ? 'check' : 'enlace'} tamano={16} />
              {estadoCopia === 'copiado'
                ? 'Enlace copiado'
                : estadoCopia === 'error'
                  ? 'No se pudo copiar'
                  : 'Copiar enlace del portal'}
            </button>
            <a
              href={urlWhatsapp}
              target="_blank"
              rel="noreferrer"
              className={`${estilos.botonSecundario} ${s.botonConIcono} ${s.botonWhatsapp}`}
            >
              <Icono nombre="mensaje" tamano={16} />
              Compartir por WhatsApp
            </a>
          </div>
        )}
      </div>

      <div className={s.filtros}>
        <button
          type="button"
          className={s.botonFiltros}
          aria-expanded={filtrosAbiertos}
          aria-controls="campos-filtro-convenios"
          onClick={() => setFiltrosAbiertos((abiertos) => !abiertos)}
        >
          <span>Filtros{activos ? ` (${activos})` : ''}</span>
          <Icono nombre="abajo" tamano={16} />
        </button>

        <div id="campos-filtro-convenios" className={s.camposFiltro} data-abierto={filtrosAbiertos} role="search">
          <div className={s.filaFiltros}>
            <label className={s.campoFiltro}>
              Buscar
              <input
                type="search"
                className={s.control}
                placeholder="Cliente o RUT"
                value={filtros.busqueda}
                onChange={(evento) => filtros.setBusqueda(evento.target.value)}
              />
            </label>
            <label className={s.campoFiltro}>
              Estado
              <select className={s.control} value={estado} onChange={(evento) => filtros.cambiar({ estado: evento.target.value })}>
                <option value="">Todos</option>
                {Object.entries(ESTADOS_CONVENIO).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            </label>
            {conFiltros && (
              <button type="button" className={s.botonLimpiar} onClick={() => filtros.cambiar({ q: '', estado: '' })}>
                <Icono nombre="cerrar" tamano={15} />
                Limpiar
              </button>
            )}
          </div>
        </div>
      </div>

      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando convenios" columnas={6} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="la página" reintentar={() => void lista.refetch()} />
      ) : lista.data.results.length === 0 ? (
        <div className={s.vacio}>
          <div className={s.iconoVacio} aria-hidden="true">
            <Icono nombre="convenios" tamano={24} />
          </div>
          {conFiltros ? (
            <>
              <p>Ningún convenio coincide con los filtros.</p>
              <button type="button" className={estilos.botonSecundario} onClick={() => filtros.cambiar({ q: '', estado: '' })}>
                Quitar filtros
              </button>
            </>
          ) : (
            <p>Aún no hay convenios. Las empresas cliente se registran desde el portal.</p>
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
          <div className={s.contenedorTabla}>
            <table className={s.tablaConvenios} aria-busy={lista.isPlaceholderData || undefined}>
              <thead>
                <tr>
                  <th scope="col">Cliente</th>
                  <th scope="col" className={s.colRut}>
                    RUT
                  </th>
                  <th scope="col" className={s.colAcceso}>
                    Acceso
                  </th>
                  <th scope="col" className={s.colReservas}>
                    Reservas
                  </th>
                  <th scope="col" className={s.colEstado}>
                    Estado
                  </th>
                  <th scope="col" className={s.colAccion}>
                    <span className="solo-lector">Acción</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {lista.data.results.map((convenio) => (
                  <tr key={convenio.id}>
                    <td data-titulo="Cliente">
                      <div>
                        <Link to={`/convenios/${convenio.id}`} className={s.enlaceCliente}>
                          {convenio.cliente_nombre}
                        </Link>
                      </div>
                    </td>
                    <td data-titulo="RUT" className={s.colRut}>
                      <div>
                        <span className={s.rut}>{convenio.cliente_rut}</span>
                      </div>
                    </td>
                    <td data-titulo="Acceso" className={s.colAcceso}>
                      <div>
                        <span className={s.badgeAcceso} data-cuenta={String(convenio.tiene_cuenta)}>
                          {convenio.tiene_cuenta ? 'Cuenta web' : 'Sin cuenta'}
                        </span>
                      </div>
                    </td>
                    <td data-titulo="Reservas" className={s.colReservas}>
                      <div>
                        <span className={s.pillReservas}>{numero.format(convenio.reservas)}</span>
                      </div>
                    </td>
                    <td data-titulo="Estado" className={s.colEstado}>
                      <div>
                        <BadgeEstado estado={convenio.estado} />
                      </div>
                    </td>
                    <td data-titulo="Acción" className={s.colAccion}>
                      <div>
                        <Link to={`/convenios/${convenio.id}`} className={s.enlaceDetalle}>
                          Ver ficha
                        </Link>
                      </div>
                    </td>
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
