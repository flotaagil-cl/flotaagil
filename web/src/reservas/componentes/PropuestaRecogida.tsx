import { useState } from 'react';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { formatearFechaHora } from '../../hora/hora';
import { useDecidirRecogida, type ViajeDetalle } from '../api';
import { mensajeDeErrorApi } from '../errores';

/** HU-27: la ETA del vuelo cambió. La recogida no cambia hasta que el despachador lo confirma (RN-02). */
export function PropuestaRecogida({ viaje }: { viaje: ViajeDetalle }) {
  const decidir = useDecidirRecogida(viaje.id);
  const [falla, setFalla] = useState<string | null>(null);
  const vuelo = viaje.vuelo;
  if (!vuelo?.recogida_propuesta) return falla ? <Aviso tipo="error">{falla}</Aviso> : null;
  const recogida_propuesta = vuelo.recogida_propuesta;

  async function resolver(confirmar: boolean) {
    setFalla(null);
    try {
      await decidir.mutateAsync({ confirmar, recogida_propuesta });
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    }
  }

  return (
    <div className={estilos.tarjeta} role="region" aria-labelledby="titulo-propuesta">
      <h2 id="titulo-propuesta">Cambió la llegada del vuelo</h2>
      <p>
        El vuelo {vuelo.numero} ahora llega {formatearFechaHora(vuelo.hora_estimada ?? vuelo.hora_programada)}. Hora de recogida
        propuesta: <strong>{formatearFechaHora(recogida_propuesta)}</strong> (actual: {formatearFechaHora(viaje.recogida_en)}).
      </p>
      <p className={estilos.explicacion}>La recogida no cambia hasta que lo confirmes.</p>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <div className={estilos.acciones}>
        <button type="button" className={estilos.boton} disabled={decidir.isPending} onClick={() => void resolver(true)}>
          Confirmar nueva hora
        </button>
        <button type="button" className={estilos.botonSecundario} disabled={decidir.isPending} onClick={() => void resolver(false)}>
          Mantener la hora actual
        </button>
      </div>
    </div>
  );
}
