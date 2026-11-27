import { useState } from 'react';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { mensajeDeErrorApi } from '../../reservas/errores';
import { useTerminarTurno, type Conductor } from '../api';
import s from '../flota.module.css';

const MAXIMO = 200;

/**
 * HU-31 (DC-32): «Terminar turno» del administrador, para el conductor que olvidó terminarlo y cuyo turno no se
 * puede cuadrar. Pide motivo y confirmación; queda en auditoría (CIERRE_ADMINISTRATIVO). En viaje no se puede.
 */
export function TerminarTurno({ conductor }: { conductor: Conductor }) {
  const terminar = useTerminarTurno(conductor.id);
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [listo, setListo] = useState(false);

  if (conductor.estado === 'NO_DISPONIBLE') {
    return listo ? <Aviso>Turno terminado. Ya puedes cerrar su caja en «Cierre de caja».</Aviso> : null;
  }

  async function confirmar() {
    if (!motivo.trim()) {
      setError('Indica el motivo.');
      return;
    }
    setError(null);
    try {
      await terminar.mutateAsync(motivo.trim());
      setListo(true);
      setAbierto(false);
    } catch (falla) {
      setError(mensajeDeErrorApi(falla));
    }
  }

  return (
    <div className={s.tarjeta}>
      <div className={s.cabeceraTarjeta}>
        <h2>Turno</h2>
        <span className={s.badge} data-tono={conductor.estado === 'EN_VIAJE' ? 'info' : 'ok'}>
          <Icono nombre={conductor.estado === 'EN_VIAJE' ? 'auto' : 'reloj'} tamano={13} />
          {conductor.estado === 'EN_VIAJE' ? 'En viaje' : 'En turno'}
        </span>
      </div>
      {conductor.estado === 'EN_VIAJE' ? (
        <p className={s.notaEstado}>Está en un viaje: el turno termina cuando lo cierre (RN-03).</p>
      ) : abierto ? (
        <div className={s.panelPeligro} role="alertdialog" aria-labelledby="pregunta-turno">
          <p id="pregunta-turno">
            {conductor.nombre} quedará No disponible y su turno se cerrará como cierre administrativo. Queda en auditoría.
          </p>
          {error && <Aviso tipo="error">{error}</Aviso>}
          <label className={s.campoTextarea}>
            Motivo
            <textarea className={s.textarea} rows={3} maxLength={MAXIMO} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
          </label>
          <span className={s.contadorMotivo}>
            {motivo.length}/{MAXIMO}
          </span>
          <div className={estilos.acciones}>
            <button type="button" className={estilos.botonPeligro} disabled={terminar.isPending} onClick={() => void confirmar()}>
              {terminar.isPending ? 'Terminando…' : 'Terminar turno'}
            </button>
            <button type="button" className={estilos.botonSecundario} disabled={terminar.isPending} onClick={() => setAbierto(false)}>
              Volver
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className={s.notaEstado}>Está en turno. Si olvidó terminarlo, puedes terminarlo tú para cuadrar su caja.</p>
          <div className={estilos.acciones}>
            <button type="button" className={estilos.botonSecundario} onClick={() => setAbierto(true)}>
              Terminar turno…
            </button>
          </div>
        </>
      )}
    </div>
  );
}
