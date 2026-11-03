import { useEffect, useState, type ReactNode } from 'react';
import { segundosRestantes, type Asignacion } from '../conductor/canal';
import { horaDeChile } from '../hora';

const pesos = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });

/**
 * Aviso de viaje asignado (HU-14): ocupa la pantalla, con los datos del viaje y la cuenta regresiva de 60 s.
 * Los botones Aceptar y Rechazar (HU-15) llegan en `acciones`.
 */
export function ViajeAsignado({ asignacion, acciones }: { asignacion: Asignacion; acciones?: ReactNode }) {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const reloj = setInterval(() => setAhora(Date.now()), 500);
    return () => clearInterval(reloj);
  }, []);
  const quedan = segundosRestantes(asignacion.vence_en, ahora);

  return (
    <main className="asignado" role="alertdialog" aria-labelledby="titulo-asignado" aria-describedby="datos-asignado">
      <h1 id="titulo-asignado">Nuevo viaje asignado</h1>
      <p className="cuenta" aria-live="assertive">
        {quedan > 0 ? `Responde en ${quedan} s` : 'Se acabó el tiempo para responder'}
      </p>
      <dl id="datos-asignado" className="tarjeta">
        <dt>Recogida</dt>
        <dd>{horaDeChile(asignacion.recogida_en)}</dd>
        <dt>Origen</dt>
        <dd>{asignacion.origen.direccion}</dd>
        <dt>Destino</dt>
        <dd>{asignacion.destino.direccion}</dd>
        <dt>Pasajero</dt>
        <dd>{asignacion.pasajero}</dd>
        <dt>Tarifa</dt>
        <dd>{asignacion.tarifa === null ? 'Por definir' : pesos.format(asignacion.tarifa)}</dd>
        {asignacion.vuelo && (
          <>
            <dt>Vuelo</dt>
            <dd>
              {asignacion.vuelo.numero} · llega {horaDeChile(asignacion.vuelo.hora_programada)}
              {asignacion.vuelo.hora_estimada && ` · ETA ${horaDeChile(asignacion.vuelo.hora_estimada)}`}
            </dd>
          </>
        )}
      </dl>
      {acciones}
    </main>
  );
}
