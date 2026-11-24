import { useEffect, useState, type ReactNode } from 'react';
import { segundosRestantes, type Asignacion } from '../conductor/canal';
import { horaDeChile } from '../hora';
import { VueloDelViaje } from './VueloDelViaje';

const pesos = new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 });
const RADIO = 34;
const PERIMETRO = 2 * Math.PI * RADIO;
const PLAZO_S = 60;

/**
 * Tarjeta prioritaria de viaje asignado (HU-14): aparece en la parte superior del Inicio con los datos del viaje
 * y la cuenta regresiva de 60 s. Los botones Aceptar viaje y Rechazar (HU-15) llegan en `acciones`.
 */
export function ViajeAsignado({ asignacion, acciones }: { asignacion: Asignacion; acciones?: ReactNode }) {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const reloj = setInterval(() => setAhora(Date.now()), 500);
    return () => clearInterval(reloj);
  }, []);
  const quedan = segundosRestantes(asignacion.vence_en, ahora);
  const progreso = Math.max(0, Math.min(1, quedan / PLAZO_S));

  return (
    <section className="tarjeta prioritaria asignado" aria-labelledby="titulo-asignado" aria-describedby="datos-asignado">
      <div className="asignado-cabecera">
        <div className="asignado-anillo" aria-hidden="true">
          <svg viewBox="0 0 80 80">
            <circle className="asignado-anillo-base" cx="40" cy="40" r={RADIO} />
            <circle
              className="asignado-anillo-progreso"
              cx="40"
              cy="40"
              r={RADIO}
              strokeDasharray={PERIMETRO}
              strokeDashoffset={PERIMETRO * (1 - progreso)}
            />
          </svg>
          <span className="asignado-segundos">{quedan}</span>
        </div>
        <div className="asignado-titulos">
          <h2 id="titulo-asignado">Nuevo viaje asignado</h2>
          <p className="cuenta" aria-live="assertive">
            {quedan > 0 ? `Responde en ${quedan} s` : 'Se acabó el tiempo para responder'}
          </p>
        </div>
      </div>

      <div className="asignado-datos-caja">
        <dl id="datos-asignado" className="lista-datos">
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
          <VueloDelViaje vuelo={asignacion.vuelo} enAeropuerto={asignacion.en_aeropuerto_a_las} />
        </dl>
      </div>
      {acciones}
    </section>
  );
}
