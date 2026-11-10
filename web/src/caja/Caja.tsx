import { useState } from 'react';
import { Aviso } from '../componentes/Aviso';
import estilos from '../componentes/panel.module.css';
import { Celda, Esqueleto, FallaDeCarga } from '../flota/componentes/comunes';
import { formatearFechaHora } from '../hora/hora';
import { useTurnosPorCerrar, type CierreCaja, type TurnoPorCerrar } from './api';
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

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Cierre de caja</h1>
      </div>
      <p>Turnos terminados con su efectivo registrado. La liquidación por día sigue en Reportes.</p>
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
        <div className={estilos.vacio}>
          <p>No hay turnos terminados por cerrar.</p>
        </div>
      ) : (
        <table className={estilos.tabla} aria-label="Turnos por cerrar">
          <thead>
            <tr>
              <th scope="col">Conductor</th>
              <th scope="col">Vehículo</th>
              <th scope="col">Turno</th>
              <th scope="col">Viajes</th>
              <th scope="col">Efectivo registrado</th>
              <th scope="col">Acción</th>
            </tr>
          </thead>
          <tbody>
            {lista.data.map((turno) => (
              <tr key={turno.id}>
                <Celda titulo="Conductor">{turno.conductor}</Celda>
                <Celda titulo="Vehículo">{turno.patente ?? '—'}</Celda>
                <Celda titulo="Turno">
                  {formatearFechaHora(turno.hora_inicio)} a {turno.hora_termino ? formatearFechaHora(turno.hora_termino) : '—'}
                  {turno.motivo_termino && turno.motivo_termino !== 'CONDUCTOR' && <> · {MOTIVOS[turno.motivo_termino]}</>}
                </Celda>
                <Celda titulo="Viajes">{turno.viajes_finalizados}</Celda>
                <Celda titulo="Efectivo registrado">{pesos.format(turno.efectivo_registrado)}</Celda>
                <Celda titulo="Acción">
                  {turno.con_viaje_en_ejecucion ? (
                    <span>Tiene un viaje en ejecución</span>
                  ) : (
                    <button type="button" className={estilos.botonSecundario} onClick={() => setAbierto(turno)}>
                      Cerrar caja…
                    </button>
                  )}
                </Celda>
              </tr>
            ))}
          </tbody>
        </table>
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
