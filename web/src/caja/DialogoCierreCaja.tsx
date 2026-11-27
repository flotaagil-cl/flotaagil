import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Aviso } from '../componentes/Aviso';
import panel from '../componentes/panel.module.css';
import { Icono } from '../diseno/Icono';
import { Campo } from '../formularios/Campo';
import { formatearFechaHora } from '../hora/hora';
import { mensajeDeErrorApi } from '../reservas/errores';
import { useCerrarCaja, type CierreCaja, type TurnoPorCerrar } from './api';
import caja from './caja.module.css';

const pesos = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
const MAXIMO = 200;

interface Props {
  turno: TurnoPorCerrar;
  alCerrar: () => void;
  alTerminar: (cierre: CierreCaja) => void;
}

/** CP-36: el administrador ingresa lo rendido; si no cuadra con lo registrado, explica la diferencia. */
export function DialogoCierreCaja({ turno, alCerrar, alTerminar }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const cerrar = useCerrarCaja(turno.id);
  const [rendido, setRendido] = useState('');
  const [observacion, setObservacion] = useState('');
  const [errores, setErrores] = useState<{ rendido?: string; observacion?: string }>({});
  const [falla, setFalla] = useState<string | null>(null);

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento || elemento.open) return;
    if (typeof elemento.showModal === 'function') elemento.showModal();
    else elemento.setAttribute('open', '');
    return () => {
      if (typeof elemento.close === 'function') elemento.close();
      else elemento.removeAttribute('open');
    };
  }, []);

  const monto = /^\d{1,8}$/.test(rendido.trim()) ? Number(rendido.trim()) : null;
  const diferencia = monto === null ? null : monto - turno.efectivo_registrado;
  const requiereObservacion = diferencia !== null && diferencia !== 0;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const nuevos: typeof errores = {};
    if (monto === null) nuevos.rendido = 'Ingresa el efectivo rendido, en pesos enteros.';
    if (requiereObservacion && !observacion.trim()) {
      nuevos.observacion = 'Explica la diferencia entre lo rendido y lo registrado.';
    }
    setErrores(nuevos);
    if (Object.keys(nuevos).length || monto === null) return;
    setFalla(null);
    try {
      const cierre = await cerrar.mutateAsync({ monto_rendido: monto, ...(observacion.trim() && { observacion: observacion.trim() }) });
      alTerminar(cierre);
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    }
  }

  return (
    <dialog
      ref={dialogo}
      className={panel.dialogo}
      aria-labelledby="titulo-cierre-caja"
      onCancel={(evento) => {
        evento.preventDefault();
        if (!cerrar.isPending) alCerrar();
      }}
    >
      <form onSubmit={(evento) => void enviar(evento)} noValidate>
        <h2 id="titulo-cierre-caja">Cerrar la caja del turno de {turno.conductor}</h2>
        <p className={caja.subtituloDialogo}>
          {turno.patente ? <span className={caja.patente}>{turno.patente}</span> : <span>Vehículo sin registrar</span>}
          <span className={caja.rangoTurno}>
            <span className={caja.fechaHora}>{formatearFechaHora(turno.hora_inicio)}</span>
            <span className={caja.conector}>a</span>
            <span className={caja.fechaHora}>{turno.hora_termino ? formatearFechaHora(turno.hora_termino) : '—'}</span>
          </span>
        </p>
        <div className={caja.resumenDialogo}>
          <span className={caja.etiquetaResumen}>Efectivo registrado:</span>
          <strong className={caja.montoResumen}>{pesos.format(turno.efectivo_registrado)}</strong>
          <span className={caja.viajesResumen}>
            en {turno.viajes_finalizados} {turno.viajes_finalizados === 1 ? 'viaje finalizado' : 'viajes finalizados'}.
          </span>
        </div>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <div className={caja.filaRendicion}>
          <Campo etiqueta="Efectivo rendido (CLP)" error={errores.rendido}>
            {(control) => <input {...control} inputMode="numeric" value={rendido} onChange={(e) => setRendido(e.target.value)} />}
          </Campo>
          {turno.efectivo_registrado > 0 && (
            <button
              type="button"
              className={caja.botonIgualar}
              onClick={() => {
                setRendido(String(turno.efectivo_registrado));
                setErrores((prev) => ({ ...prev, rendido: undefined, observacion: undefined }));
              }}
              disabled={cerrar.isPending}
            >
              <Icono nombre="check" tamano={14} />
              <span>Igualar monto registrado ({pesos.format(turno.efectivo_registrado)})</span>
            </button>
          )}
        </div>
        {diferencia !== null && (
          <div
            className={caja.diferenciaPill}
            data-estado={diferencia === 0 ? 'ok' : diferencia < 0 ? 'peligro' : 'info'}
            aria-live="polite"
          >
            <Icono nombre={diferencia === 0 ? 'check' : diferencia < 0 ? 'alerta' : 'info'} tamano={16} />
            <span>
              {diferencia === 0
                ? 'Cuadra con lo registrado.'
                : diferencia < 0
                  ? `Faltan ${pesos.format(-diferencia)}.`
                  : `Sobran ${pesos.format(diferencia)}.`}
            </span>
          </div>
        )}
        <Campo etiqueta="Observación" error={errores.observacion}>
          {(control) => (
            <textarea {...control} rows={3} maxLength={MAXIMO} value={observacion} onChange={(e) => setObservacion(e.target.value)} />
          )}
        </Campo>
        {requiereObservacion && (
          <p className={caja.ayudaCampo}>Obligatoria cuando el monto rendido no coincide con lo registrado.</p>
        )}
        <div className={panel.acciones}>
          <button type="submit" className={panel.boton} disabled={cerrar.isPending}>
            {cerrar.isPending ? 'Cerrando…' : 'Cerrar caja'}
          </button>
          <button type="button" className={panel.botonSecundario} onClick={alCerrar} disabled={cerrar.isPending}>
            Volver
          </button>
        </div>
      </form>
    </dialog>
  );
}
