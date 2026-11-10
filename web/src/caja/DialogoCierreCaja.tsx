import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Aviso } from '../componentes/Aviso';
import estilos from '../componentes/panel.module.css';
import { Campo } from '../formularios/Campo';
import { formatearFechaHora } from '../hora/hora';
import { mensajeDeErrorApi } from '../reservas/errores';
import { useCerrarCaja, type CierreCaja, type TurnoPorCerrar } from './api';

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

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const nuevos: typeof errores = {};
    if (monto === null) nuevos.rendido = 'Ingresa el efectivo rendido, en pesos enteros.';
    if (diferencia !== null && diferencia !== 0 && !observacion.trim()) {
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
      className={estilos.dialogo}
      aria-labelledby="titulo-cierre-caja"
      onCancel={(evento) => {
        evento.preventDefault();
        if (!cerrar.isPending) alCerrar();
      }}
    >
      <form onSubmit={(evento) => void enviar(evento)} noValidate>
        <h2 id="titulo-cierre-caja">Cerrar la caja del turno de {turno.conductor}</h2>
        <p>
          {turno.patente ?? 'Vehículo sin registrar'} · {formatearFechaHora(turno.hora_inicio)} a{' '}
          {turno.hora_termino ? formatearFechaHora(turno.hora_termino) : '—'}
        </p>
        <p>
          Efectivo registrado: <strong>{pesos.format(turno.efectivo_registrado)}</strong> en {turno.viajes_finalizados}{' '}
          {turno.viajes_finalizados === 1 ? 'viaje finalizado' : 'viajes finalizados'}.
        </p>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <Campo etiqueta="Efectivo rendido (CLP)" error={errores.rendido}>
          {(control) => <input {...control} inputMode="numeric" value={rendido} onChange={(e) => setRendido(e.target.value)} />}
        </Campo>
        {diferencia !== null && (
          <p aria-live="polite">
            {diferencia === 0
              ? 'Cuadra con lo registrado.'
              : diferencia < 0
                ? `Faltan ${pesos.format(-diferencia)}.`
                : `Sobran ${pesos.format(diferencia)}.`}
          </p>
        )}
        <Campo etiqueta="Observación" error={errores.observacion}>
          {(control) => (
            <textarea {...control} rows={3} maxLength={MAXIMO} value={observacion} onChange={(e) => setObservacion(e.target.value)} />
          )}
        </Campo>
        <div className={estilos.acciones}>
          <button type="submit" className={estilos.boton} disabled={cerrar.isPending}>
            {cerrar.isPending ? 'Cerrando…' : 'Cerrar caja'}
          </button>
          <button type="button" className={estilos.botonSecundario} onClick={alCerrar} disabled={cerrar.isPending}>
            Volver
          </button>
        </div>
      </form>
    </dialog>
  );
}
