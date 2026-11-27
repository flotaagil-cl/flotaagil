import { useState, type ReactNode } from 'react';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../../flota/componentes/comunes';
import { useFiltrosUrl } from '../../flota/filtrosUrl';
import { formatearFechaHora, hoy, sumarDias } from '../../hora/hora';
import type { EstadoViaje } from '../../reservas/api';
import { EstadoEtiqueta } from '../../reservas/componentes/EstadoEtiqueta';
import { mensajeDeErrorApi } from '../../reservas/errores';
import { ESTADOS } from '../../reservas/etiquetas';
import { useDescargarCsv, useOpcionesReporte, useReporte, type Columna, type FiltrosReporte, type TipoReporte } from '../api';
import propios from '../reportes.module.css';

const TIPOS: { valor: TipoReporte; texto: string; ayuda: string }[] = [
  { valor: 'liquidacion', texto: 'Liquidación por conductor', ayuda: 'Viajes finalizados por día del pago. Incluye los cierres forzados, identificados en sus columnas.' },
  { valor: 'facturacion', texto: 'Facturación por convenio', ayuda: 'Viajes finalizados de cada convenio, por día del pago.' },
  { valor: 'cancelaciones', texto: 'Cancelaciones', ayuda: 'Tasa de cancelación por origen, sobre las reservas con recogida en el período.' },
  { valor: 'historial', texto: 'Historial de viajes', ayuda: 'Todas las reservas con recogida en el período.' },
  {
    valor: 'contingencia',
    texto: 'Conciliación de contingencia',
    ayuda: 'Reservas de contingencia por folio, según el día de recogida real, con sus montos. «Sin turno»: el conductor no tenía un turno que contuviera la hora real.',
  },
];

const ESTADO_POR_ETIQUETA = Object.fromEntries(
  (Object.entries(ESTADOS) as [EstadoViaje, string][]).map(([clave, etiqueta]) => [etiqueta, clave]),
) as Record<string, EstadoViaje>;

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

interface Metrica {
  etiqueta: string;
  valor: string;
  destacada?: boolean;
}

function metricasDe(
  tipo: TipoReporte,
  totales: Record<string, unknown>,
  consulta: FiltrosReporte,
  count: number,
): Metrica[] {
  if (tipo === 'liquidacion' || tipo === 'facturacion') {
    const cierres = formatear(totales.cierres_forzados, 'entero');
    const montoCierres =
      totales.monto_cierres_forzados !== undefined && Number(totales.monto_cierres_forzados) > 0
        ? ` (${formatear(totales.monto_cierres_forzados, 'pesos')})`
        : '';
    return [
      { etiqueta: 'Total del período', valor: formatear(totales.total, 'pesos'), destacada: true },
      { etiqueta: 'Viajes finalizados', valor: formatear(totales.viajes, 'entero') },
      { etiqueta: 'Cierres forzados', valor: `${cierres}${montoCierres}` },
    ];
  }
  if (tipo === 'cancelaciones') {
    const base =
      typeof totales.origen === 'string'
        ? (totales.origen.match(/(\d[\d.]*\s+reservas?)/i)?.[1] ?? totales.origen)
        : '—';
    return [
      { etiqueta: 'Tasa KPI-01', valor: formatear(totales.tasa, 'porcentaje'), destacada: true },
      { etiqueta: 'Reservas perdidas', valor: formatear(totales.cantidad, 'entero') },
      { etiqueta: 'Base evaluada', valor: base },
    ];
  }
  if (tipo === 'historial') {
    return [
      { etiqueta: 'Total pagado', valor: formatear(totales.monto, 'pesos'), destacada: true },
      { etiqueta: 'Reservas en el período', valor: formatear(totales.id ?? count, 'entero') },
      { etiqueta: 'Período', valor: `${formatear(consulta.desde, 'fecha')} al ${formatear(consulta.hasta, 'fecha')}` },
    ];
  }
  return [
    { etiqueta: 'Total conciliado', valor: formatear(totales.monto ?? totales.total ?? 0, 'pesos'), destacada: true },
    { etiqueta: 'Registros', valor: formatear(count, 'entero') },
    { etiqueta: 'Período', valor: `${formatear(consulta.desde, 'fecha')} al ${formatear(consulta.hasta, 'fecha')}` },
  ];
}

function renderValor(columna: Columna, valor: unknown, esTotal: boolean, tipo: TipoReporte): ReactNode {
  if (esTotal) {
    const texto = formatear(valor, columna.tipo);
    if (tipo === 'historial' && columna.clave === 'id') return `Total: ${texto}`;
    if (columna.tipo === 'texto') return <span className={propios.textoTotal}>{texto}</span>;
    return <span className={propios.sinCorte}>{texto}</span>;
  }

  if ((columna.clave === 'estado' || columna.clave === 'resultado') && typeof valor === 'string') {
    const estado = ESTADO_POR_ETIQUETA[valor];
    if (estado) return <EstadoEtiqueta estado={estado} />;
  }

  const texto = formatear(valor, columna.tipo);
  if (columna.tipo === 'pesos' && valor !== null && valor !== undefined && valor !== '') {
    return <span className={Number(valor) > 0 ? propios.montoPositivo : propios.montoCero}>{texto}</span>;
  }
  if (columna.tipo === 'fecha' || columna.tipo === 'fecha_hora' || columna.tipo === 'entero' || columna.tipo === 'porcentaje' || columna.clave === 'rut') {
    return <span className={propios.sinCorte}>{texto}</span>;
  }
  if (columna.clave === 'origen' || columna.clave === 'destino') {
    return <span className={propios.celdaDireccion}>{texto}</span>;
  }
  return texto;
}

/** HU-06: reportes con filtros, totales del período y exportación CSV. */
export function Reportes() {
  const filtros = useFiltrosUrl(['tipo', 'desde', 'hasta', 'conductor', 'convenio'] as const);
  const { valores } = filtros;
  const [filtrosAbiertos, setFiltrosAbiertos] = useState(false);
  const hoyTexto = hoy();
  const hace7Dias = sumarDias(hoyTexto, -6);
  const hace30Dias = sumarDias(hoyTexto, -29);
  const inicioMes = `${hoyTexto.slice(0, 7)}-01`;

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

  const atajos = [
    { etiqueta: 'Hoy', desde: hoyTexto, hasta: hoyTexto },
    { etiqueta: 'Últimos 7 días', desde: hace7Dias, hasta: hoyTexto },
    { etiqueta: 'Últimos 30 días', desde: hace30Dias, hasta: hoyTexto },
    { etiqueta: 'Este mes', desde: inicioMes, hasta: hoyTexto },
  ];

  const hayCambios =
    tipo !== 'liquidacion' ||
    consulta.desde !== hoyTexto ||
    consulta.hasta !== hoyTexto ||
    Boolean(valores.conductor) ||
    Boolean(valores.convenio);

  const metricas =
    reporte.data && reporte.data.filas.length > 0
      ? metricasDe(tipo, reporte.data.totales, consulta, reporte.data.count)
      : null;

  return (
    <section>
      <div className={propios.encabezado}>
        <div className={propios.tituloBloque}>
          <h1>Reportes</h1>
          <p className={propios.subtitulo}>{definicion.ayuda}</p>
        </div>
        <button
          type="button"
          className={`${estilos.boton} ${propios.botonExportar}`}
          disabled={descargar.isPending || reporte.isError || !fechasValidas}
          onClick={() => descargar.mutate({ tipo, filtros: consulta })}
        >
          <Icono nombre="descargar" tamano={18} />
          <span>{descargar.isPending ? 'Preparando…' : 'Exportar CSV'}</span>
        </button>
      </div>
      {descargar.isError && <Aviso tipo="error">{mensajeDeErrorApi(descargar.error)}</Aviso>}

      <div className={propios.filtros}>
        <button
          type="button"
          className={propios.botonFiltros}
          aria-expanded={filtrosAbiertos}
          onClick={() => setFiltrosAbiertos((abierto) => !abierto)}
        >
          <span>Filtros · {definicion.texto}</span>
          <Icono nombre="abajo" tamano={18} />
        </button>
        <div className={propios.camposFiltro} data-abierto={filtrosAbiertos}>
          <div className={propios.filaPrincipal}>
            <label className={propios.campoFiltro}>
              <span>Reporte</span>
              <select className={propios.control} value={tipo} onChange={(evento) => filtros.cambiar({ tipo: evento.target.value })}>
                {TIPOS.map((t) => (
                  <option key={t.valor} value={t.valor}>
                    {t.texto}
                  </option>
                ))}
              </select>
            </label>
            <label className={propios.campoFiltro}>
              <span>Desde</span>
              <input className={propios.control} type="date" value={consulta.desde} onChange={(evento) => filtros.cambiar({ desde: evento.target.value })} />
            </label>
            <label className={propios.campoFiltro}>
              <span>Hasta</span>
              <input className={propios.control} type="date" value={consulta.hasta} onChange={(evento) => filtros.cambiar({ hasta: evento.target.value })} />
            </label>
          </div>
          <div className={propios.filaSecundaria}>
            <label className={propios.campoFiltro}>
              <span>Conductor</span>
              <select className={propios.control} value={valores.conductor} onChange={(evento) => filtros.cambiar({ conductor: evento.target.value })}>
                <option value="">Todos</option>
                {opciones.data?.conductores.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className={propios.campoFiltro}>
              <span>Convenio</span>
              <select className={propios.control} value={valores.convenio} onChange={(evento) => filtros.cambiar({ convenio: evento.target.value })}>
                <option value="">Todos</option>
                {opciones.data?.convenios.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.nombre}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className={propios.barraAtajos}>
            <span className={propios.etiquetaAtajos}>Rango rápido:</span>
            {atajos.map((atajo) => {
              const activo = consulta.desde === atajo.desde && consulta.hasta === atajo.hasta;
              return (
                <button
                  key={atajo.etiqueta}
                  type="button"
                  className={propios.chipRango}
                  aria-pressed={activo}
                  onClick={() => filtros.cambiar({ desde: atajo.desde, hasta: atajo.hasta })}
                >
                  {atajo.etiqueta}
                </button>
              );
            })}
            {hayCambios && (
              <button
                type="button"
                className={propios.botonLimpiar}
                onClick={() => filtros.cambiar({ tipo: '', desde: '', hasta: '', conductor: '', convenio: '' })}
              >
                Restablecer
              </button>
            )}
          </div>
        </div>
      </div>

      {!fechasValidas ? (
        <Aviso tipo="error">La fecha inicial no puede ser posterior a la final.</Aviso>
      ) : reporte.isPending ? (
        <Esqueleto etiqueta="Cargando el reporte" columnas={5} />
      ) : reporte.isError ? (
        <FallaDeCarga error={reporte.error} que="el reporte" reintentar={() => void reporte.refetch()} />
      ) : reporte.data.filas.length === 0 ? (
        <div className={propios.vacio}>
          <span className={propios.iconoVacio} aria-hidden="true">
            <Icono nombre="calendario" tamano={24} />
          </span>
          <p>Sin datos en este período.</p>
          {consulta.desde === consulta.hasta && (
            <div className={propios.accionesVacio}>
              <button
                type="button"
                className={propios.chipRango}
                onClick={() => filtros.cambiar({ desde: hace7Dias, hasta: hoyTexto })}
              >
                Ver últimos 7 días
              </button>
              <button
                type="button"
                className={propios.chipRango}
                onClick={() => filtros.cambiar({ desde: inicioMes, hasta: hoyTexto })}
              >
                Ver este mes
              </button>
            </div>
          )}
        </div>
      ) : (
        <>
          {metricas && (
            <div className={propios.resumenMetricas} aria-label="Resumen del reporte">
              {metricas.map((m) => (
                <div key={m.etiqueta} className={`${propios.tarjetaMetrica} ${m.destacada ? propios.tarjetaMetricaDestacada : ''}`}>
                  <span className={propios.etiquetaMetrica}>{m.etiqueta}</span>
                  <strong className={propios.valorMetrica}>{m.valor}</strong>
                </div>
              ))}
            </div>
          )}

          <div className={propios.barraTabla}>
            <span>
              {reporte.data.count} {reporte.data.count === 1 ? 'registro' : 'registros'} en el período
            </span>
            {reporte.data.columnas.length >= 11 && (
              <span className={propios.pistaScroll}>
                <Icono nombre="flechaDerecha" tamano={14} />
                <span>Desliza la tabla horizontalmente para ver todas las columnas</span>
              </span>
            )}
          </div>

          <div className={`${propios.contenedorTabla} ${propios.desplazable}`}>
            <table className={propios.tablaReporte} aria-label={definicion.texto} aria-busy={reporte.isPlaceholderData || undefined}>
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
                        {renderValor(c, fila[c.clave], false, tipo)}
                      </Celda>
                    ))}
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr className={propios.totales}>
                  {reporte.data.columnas.map((c) => {
                    const tieneTotal = c.clave in reporte.data.totales;
                    return (
                      <Celda key={c.clave} titulo={c.titulo} className={tieneTotal ? undefined : propios.celdaTotalVacia}>
                        {tieneTotal ? renderValor(c, reporte.data.totales[c.clave], true, tipo) : ''}
                      </Celda>
                    );
                  })}
                </tr>
              </tfoot>
            </table>
          </div>
          <div className={propios.pieTabla}>
            <span className={propios.infoPagina}>Página {filtros.pagina}</span>
            <Paginacion
              anterior={Boolean(reporte.data.previous)}
              siguiente={Boolean(reporte.data.next)}
              pagina={filtros.pagina}
              ir={(pagina) => filtros.cambiar({ page: String(pagina) })}
            />
          </div>
        </>
      )}
    </section>
  );
}
