import { useEffect, useState } from 'react';
import { Icono } from '../componentes/Icono';
import { segundosRestantes, type Asignacion } from '../conductor/canal';

interface Props {
  asignacion: Asignacion;
  /** Envía la respuesta; resuelve con el mensaje de error, o null si se registró. */
  responder: (aceptar: boolean) => Promise<string | null>;
  ocultar: () => void;
}

/** Botones Aceptar y Rechazar del viaje asignado (HU-15). Se desactivan al terminar los 60 s (RN-04). */
export function Responder({ asignacion, responder, ocultar }: Props) {
  const [enviando, setEnviando] = useState<'aceptar' | 'rechazar' | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const reloj = setInterval(() => setAhora(Date.now()), 500);
    return () => clearInterval(reloj);
  }, []);
  const vencida = segundosRestantes(asignacion.vence_en, ahora) === 0;

  async function enviar(aceptar: boolean) {
    setEnviando(aceptar ? 'aceptar' : 'rechazar');
    setFalla(null);
    const error = await responder(aceptar);
    if (error) setFalla(error);
    setEnviando(null);
  }

  return (
    <>
      {falla && (
        <p className="error alerta-bloque" role="alert">
          <Icono nombre="alerta" tamano={18} />
          <span>{falla}</span>
        </p>
      )}
      {vencida ? (
        <div className="asignado-vencida">
          <p className="aviso alerta-bloque">
            <Icono nombre="reloj" tamano={18} />
            <span>El viaje volvió a la central para reasignarlo.</span>
          </p>
          <button className="principal" type="button" onClick={ocultar}>
            Entendido
          </button>
        </div>
      ) : (
        <div className="responder">
          <button className="principal" type="button" disabled={enviando !== null} onClick={() => void enviar(true)}>
            {enviando === 'aceptar' ? 'Aceptando…' : 'Aceptar viaje'}
          </button>
          <button className="principal rechazar" type="button" disabled={enviando !== null} onClick={() => void enviar(false)}>
            {enviando === 'rechazar' ? 'Rechazando…' : 'Rechazar'}
          </button>
        </div>
      )}
    </>
  );
}
