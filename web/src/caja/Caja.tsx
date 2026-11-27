import { useMemo, useState } from 'react';
import { Aviso } from '../componentes/Aviso';
import panel from '../componentes/panel.module.css';
import { Icono } from '../diseno/Icono';
import { Celda, Esqueleto, FallaDeCarga } from '../flota/componentes/comunes';
import { formatearFechaHora } from '../hora/hora';
import { useTurnosPorCerrar, type CierreCaja, type TurnoPorCerrar } from './api';
import caja from './caja.module.css';
import { DialogoCierreCaja } from './DialogoCierreCaja';

const pesos = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

const MOTIVOS: Record<string, string> = {
  CONDUCTOR: 'Lo terminó el conductor',
  CUENTA_DESHABILITADA: 'Cuenta deshabilitada',
  CIERRE_ADMINISTRATIVO: 'Cierre administrativo',
};

/** HU-31: turnos terminados sin cierre de caja; el administrador cuadra el efectivo de cada uno. */
export function Caja() {
  const lista = useTurnosPorCerrar();
  const [abierto, setAbierto] = useState<TurnoPorCerrar | null>(null);
  const [ultimo, setUltimo] = useState<{ turno: TurnoPorCerrar; cierre: CierreCaja } | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [soloConEfectivo, setSoloConEfectivo] = useState(false);

  const resumen = useMemo(() => {
    const turnos = lista.data ?? [];
    let conEfectivo = 0;
    let totalEfectivo = 0;
    for (const turno of turnos) {
      if (turno.efectivo_registrado > 0) {
        conEfectivo += 1;
        totalEfectivo += turno.efectivo_registrado;
      }
    }
    return { total: turnos.length, conEfectivo, totalEfectivo };
  }, [lista.data]);

  const filtrados = useMemo(() => {
    const turnos = lista.data ?? [];
    const termino = busqueda.trim().toLowerCase();
    return turnos.filter((turno) => {
      if (soloConEfectivo && turno.efectivo_registrado <= 0) return false;
      if (!termino) return true;
      return (
        turno.conductor.toLowerCase().includes(termino) ||
        (turno.patente?.toLowerCase().includes(termino) ?? false)
      );
    });
  }, [lista.data, busqueda, soloConEfectivo]);

  const hayFiltros = busqueda.trim() !== '' || soloConEfectivo;

  return (
    <section>
      <div className={caja.encabezado}>
        <div className={caja.tituloBloque}>
          <h1>Cierre de caja</h1>
          <p className={caja.subtitulo}>
            Turnos terminados con su efectivo registrado. La liquidación por día sigue en Reportes.
          </p>
        </div>
      </div>

      {ultimo && (
        <Aviso>
          Caja cerrada para {ultimo.turno.conductor}:{' '}
          {ultimo.cierre.diferencia === 0
            ? 'cuadra con lo registrado.'
            : ultimo.cierre.diferencia < 0
              ? `faltaron ${pesos.format(-ultimo.cierre.diferencia)}.`
              : `sobraron ${pesos.format(ultimo.cierre.diferencia)}.`}
        </Aviso>
      )}

      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando turnos" columnas={6} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="los turnos" reintentar={() => void lista.refetch()} />
      ) : lista.data.length === 0 ? (
        <div className={panel.vacio}>
          <p>No hay turnos terminados por cerrar.</p>
        </div>
      ) : (
        <>
          <div className={caja.resumenMetricas} aria-label="Resumen de caja">
            <div className={caja.tarjetaMetrica}>
              <span className={caja.etiquetaMetrica}>Turnos por cerrar</span>
              <strong className={caja.valorMetrica}>{resumen.total}</strong>
            </div>
            <div className={caja.tarjetaMetrica}>
              <span className={caja.etiquetaMetrica}>Con efectivo por rendir</span>
              <strong className={caja.valorMetrica}>{resumen.conEfectivo}</strong>
            </div>
            <div className={`${caja.tarjetaMetrica} ${resumen.totalEfectivo > 0 ? caja.tarjetaMetricaDestacada : ''}`}>
              <span className={caja.etiquetaMetrica}>Total efectivo registrado</span>
              <strong className={caja.valorMetrica}>{pesos.format(resumen.totalEfectivo)}</strong>
            </div>
          </div>

          <div className={caja.filtros} role="search" aria-label="Filtrar turnos por cerrar">
            <div className={caja.filaFiltros}>
              <label className={caja.campoBuscar}>
                <span>Buscar turno</span>
                <input
                  type="search"
                  className={caja.control}
                  placeholder="Conductor o patente…"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                />
              </label>
              <div className={caja.accionesFiltro}>
                <button
                  type="button"
                  className={caja.chipFiltro}
                  aria-pressed={soloConEfectivo}
                  onClick={() => setSoloConEfectivo((activo) => !activo)}
                >
                  {soloConEfectivo && <Icono nombre="check" tamano={15} />}
                  <span>Solo con efectivo ({resumen.conEfectivo})</span>
                </button>
                {hayFiltros && (
                  <button
                    type="button"
                    className={caja.botonLimpiar}
                    onClick={() => {
                      setBusqueda('');
                      setSoloConEfectivo(false);
                    }}
                  >
                    Limpiar
                  </button>
                )}
              </div>
            </div>
          </div>

          {filtrados.length === 0 ? (
            <div className={caja.vacioFiltrado}>
              <p>Ningún turno coincide con el filtro actual.</p>
              <button
                type="button"
                className={caja.botonLimpiar}
                onClick={() => {
                  setBusqueda('');
                  setSoloConEfectivo(false);
                }}
              >
                Limpiar filtros
              </button>
            </div>
          ) : (
            <div className={caja.contenedorTabla}>
              <table className={caja.tablaCaja} aria-label="Turnos por cerrar">
                <thead>
                  <tr>
                    <th scope="col">Conductor</th>
                    <th scope="col">Vehículo</th>
                    <th scope="col">Turno</th>
                    <th scope="col">Viajes</th>
                    <th scope="col">Efectivo registrado</th>
                    <th scope="col" className={caja.colAccion}>
                      Acción
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {filtrados.map((turno) => (
                    <tr key={turno.id}>
                      <Celda titulo="Conductor">
                        <span className={caja.nombreConductor}>{turno.conductor}</span>
                      </Celda>
                      <Celda titulo="Vehículo">
                        {turno.patente ? (
                          <span className={caja.patente}>{turno.patente}</span>
                        ) : (
                          <span className={caja.sinDato}>—</span>
                        )}
                      </Celda>
                      <Celda titulo="Turno">
                        <div className={caja.celdaTurno}>
                          <span className={caja.rangoTurno}>
                            <span className={caja.fechaHora}>{formatearFechaHora(turno.hora_inicio)}</span>
                            <span className={caja.conector}>a</span>
                            <span className={caja.fechaHora}>
                              {turno.hora_termino ? formatearFechaHora(turno.hora_termino) : '—'}
                            </span>
                          </span>
                          {turno.motivo_termino && turno.motivo_termino !== 'CONDUCTOR' && (
                            <span className={caja.badge} data-tono="neutro">
                              <Icono nombre="info" tamano={13} />
                              <span>{MOTIVOS[turno.motivo_termino]}</span>
                            </span>
                          )}
                        </div>
                      </Celda>
                      <Celda titulo="Viajes">
                        <span className={caja.numeroTabular}>{turno.viajes_finalizados}</span>
                      </Celda>
                      <Celda titulo="Efectivo registrado">
                        <span className={turno.efectivo_registrado > 0 ? caja.montoPositivo : caja.montoCero}>
                          {pesos.format(turno.efectivo_registrado)}
                        </span>
                      </Celda>
                      <Celda titulo="Acción" className={caja.colAccion}>
                        {turno.con_viaje_en_ejecucion ? (
                          <span className={caja.badge} data-tono="revision">
                            <Icono nombre="alerta" tamano={14} />
                            <span>Tiene un viaje en ejecución</span>
                          </span>
                        ) : (
                          <button type="button" className={caja.botonCerrarCaja} onClick={() => setAbierto(turno)}>
                            <Icono nombre="caja" tamano={15} />
                            <span>Cerrar caja…</span>
                          </button>
                        )}
                      </Celda>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {abierto && (
        <DialogoCierreCaja
          turno={abierto}
          alCerrar={() => setAbierto(null)}
          alTerminar={(cierre) => {
            setUltimo({ turno: abierto, cierre });
            setAbierto(null);
          }}
        />
      )}
    </section>
  );
}
