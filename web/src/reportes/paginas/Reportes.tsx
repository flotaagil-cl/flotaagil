import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../../flota/componentes/comunes';
import { useFiltrosUrl } from '../../flota/filtrosUrl';
import campos from '../../formularios/formularios.module.css';
import { formatearFechaHora, hoy } from '../../hora/hora';
import { mensajeDeErrorApi } from '../../reservas/errores';
import { useDescargarCsv, useOpcionesReporte, useReporte, type Columna, type FiltrosReporte, type TipoReporte } from '../api';
import propios from '../reportes.module.css';

const TIPOS: { valor: TipoReporte; texto: string; ayuda: string }[] = [
  { valor: 'liquidacion', texto: 'Liquidación por conductor', ayuda: 'Viajes finalizados por día del pago. Incluye los cierres forzados, identificados en sus columnas.' },
  { valor: 'facturacion', texto: 'Facturación por convenio', ayuda: 'Viajes finalizados de cada convenio, por día del pago.' },
  { valor: 'cancelaciones', texto: 'Cancelaciones', ayuda: 'Tasa de cancelación por origen, sobre las reservas con recogida en el período.' },
  { valor: 'historial', texto: 'Historial de viajes', ayuda: 'Todas las reservas con recogida en el período.' },
];

const numero = new Intl.NumberFormat('es-CL');

function formatear(valor: unknown, tipo: Columna['tipo']): string {
  if (valor === null || valor === undefined || valor === '') return '—';
  if (tipo === 'pesos') return `$${numero.format(Number(valor))}`;
  if (tipo === 'entero') return numero.format(Number(valor));
  if (tipo === 'porcentaje') return `${numero.format(Number(valor))} %`;
  if (tipo === 'fecha') return String(valor).split('-').reverse().join('-');
  if (tipo === 'fecha_hora') return formatearFechaHora(String(valor));
  return String(valor);
}

/** HU-06: reportes con filtros, totales del período y exportación CSV. */
export function Reportes() {
  const filtros = useFiltrosUrl(['tipo', 'desde', 'hasta', 'conductor', 'convenio'] as const);
  const { valores } = filtros;
  const hoyTexto = hoy();
  const tipo = (TIPOS.find((t) => t.valor === valores.tipo)?.valor ?? 'liquidacion') as TipoReporte;
  const consulta: FiltrosReporte = {
    desde: valores.desde || hoyTexto,
    hasta: valores.hasta || hoyTexto,
    ...(valores.conductor && { conductor: Number(valores.conductor) }),
    ...(valores.convenio && { convenio: Number(valores.convenio) }),
  };
  const fechasValidas = consulta.desde <= consulta.hasta;
  const reporte = useReporte(tipo, consulta, filtros.pagina, fechasValidas);
  const opciones = useOpcionesReporte();
  const descargar = useDescargarCsv();
  const definicion = TIPOS.find((t) => t.valor === tipo)!;

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Reportes</h1>
        <button type="button" className={estilos.boton} disabled={descargar.isPending || reporte.isError || !fechasValidas} onClick={() => descargar.mutate({ tipo, filtros: consulta })}>
          {descargar.isPending ? 'Preparando…' : 'Exportar CSV'}
        </button>
      </div>
      {descargar.isError && <Aviso tipo="error">{mensajeDeErrorApi(descargar.error)}</Aviso>}

      <div className={estilos.filtros}>
        <div className={estilos.camposFiltro} data-abierto="true">
          <label className={campos.campo}>
            Reporte
            <select value={tipo} onChange={(evento) => filtros.cambiar({ tipo: evento.target.value })}>
              {TIPOS.map((t) => (
                <option key={t.valor} value={t.valor}>
                  {t.texto}
                </option>
              ))}
            </select>
          </label>
          <label className={campos.campo}>
            Desde
            <input type="date" value={consulta.desde} onChange={(evento) => filtros.cambiar({ desde: evento.target.value })} />
          </label>
          <label className={campos.campo}>
            Hasta
            <input type="date" value={consulta.hasta} onChange={(evento) => filtros.cambiar({ hasta: evento.target.value })} />
          </label>
          <label className={campos.campo}>
            Conductor
            <select value={valores.conductor} onChange={(evento) => filtros.cambiar({ conductor: evento.target.value })}>
              <option value="">Todos</option>
              {opciones.data?.conductores.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className={campos.campo}>
            Convenio
            <select value={valores.convenio} onChange={(evento) => filtros.cambiar({ convenio: evento.target.value })}>
              <option value="">Todos</option>
              {opciones.data?.convenios.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nombre}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <p className={estilos.explicacion}>{definicion.ayuda}</p>

      {!fechasValidas ? (
        <Aviso tipo="error">La fecha inicial no puede ser posterior a la final.</Aviso>
      ) : reporte.isPending ? (
        <Esqueleto etiqueta="Cargando el reporte" columnas={5} />
      ) : reporte.isError ? (
        <FallaDeCarga error={reporte.error} que="el reporte" reintentar={() => void reporte.refetch()} />
      ) : reporte.data.filas.length === 0 ? (
        <div className={estilos.vacio}>
          <p>Sin datos en este período.</p>
        </div>
      ) : (
        <>
          <div className={propios.desplazable}>
            <table className={estilos.tabla} aria-label={definicion.texto} aria-busy={reporte.isPlaceholderData || undefined}>
              <thead>
                <tr>
                  {reporte.data.columnas.map((c) => (
                    <th key={c.clave} scope="col">
                      {c.titulo}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reporte.data.filas.map((fila, indice) => (
                  <tr key={indice}>
                    {reporte.data.columnas.map((c) => (
                      <Celda key={c.clave} titulo={c.titulo}>
                        {formatear(fila[c.clave], c.tipo)}
                      </Celda>
                    ))}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className={propios.totales}>
                  {reporte.data.columnas.map((c) => (
                    <Celda key={c.clave} titulo={c.titulo}>
                      {c.clave in reporte.data.totales ? formatear(reporte.data.totales[c.clave], c.tipo) : ''}
                    </Celda>
                  ))}
                </tr>
              </tfoot>
            </table>
          </div>
          <Paginacion anterior={Boolean(reporte.data.previous)} siguiente={Boolean(reporte.data.next)} pagina={filtros.pagina} ir={(pagina) => filtros.cambiar({ page: String(pagina) })} />
        </>
      )}
    </section>
  );
}
