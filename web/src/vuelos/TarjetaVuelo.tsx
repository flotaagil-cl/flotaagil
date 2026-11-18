/** HU-69: tarjeta de vuelo en el detalle de la reserva. Solo lee la base (sin consultar la API de vuelos). */

import estilos from '../componentes/panel.module.css';
import { formatearFechaHora, formatearHora } from '../hora/hora';
import type { ViajeDetalle } from '../reservas/api';
import { PropuestaRecogida } from '../reservas/componentes/PropuestaRecogida';
import { EstadoVuelo } from './LineaVuelo';
import { useAhora } from './useAhora';
import { cuentaRegresiva, enEspera, estadoDeVuelo, llegadaDe, minutosHasta, tipoDeSalida } from './textos';
import c from './vuelos.module.css';

function origenDe(internacional: boolean | null, icao: string | null): string {
  // La ciudad no está en VUELO (DC-69): solo nacional o internacional y el código del aeropuerto, si la API lo dio.
  const tipo = internacional === null ? 'Sin informar por la API de vuelos' : internacional ? 'Internacional' : 'Nacional';
  return icao ? `${tipo} (aeropuerto ${icao})` : tipo;
}

export function TarjetaVuelo({ viaje }: { viaje: ViajeDetalle }) {
  const ahora = useAhora();
  const vuelo = viaje.vuelo;

  // VUELO existe solo en las llegadas (desde el aeropuerto).
  if (vuelo) {
    const llegada = llegadaDe(vuelo);
    const falta = minutosHasta(llegada, ahora);
    const regresiva =
      vuelo.estado_vuelo === 'ATERRIZADO'
        ? `aterrizó ${cuentaRegresiva(llegada, Math.max(ahora, Date.parse(llegada)))}`
        : enEspera(vuelo)
          ? falta > 0
            ? `aterriza ${cuentaRegresiva(llegada, ahora)}`
            : 'debió aterrizar: aún sin confirmación de la API'
          : '—';
    return (
      <section className={estilos.tarjeta} aria-labelledby="titulo-vuelo">
        <h2 id="titulo-vuelo">
          Vuelo {vuelo.numero} <EstadoVuelo estado={estadoDeVuelo(vuelo, ahora)} />
        </h2>
        <div className={c.horas}>
          <p className={c.hora}>
            <span>Llegada programada</span>
            <strong>{formatearHora(vuelo.hora_programada, ahora)}</strong>
          </p>
          <p className={c.hora}>
            <span>Llegada estimada</span>
            <strong>{vuelo.hora_estimada ? formatearHora(vuelo.hora_estimada, ahora) : 'Sin estimación'}</strong>
          </p>
          <p className={c.hora}>
            <span>Cuenta regresiva</span>
            <strong>{regresiva}</strong>
          </p>
        </div>
        <dl className={estilos.datos}>
          <div>
            <dt>Origen</dt>
            <dd>{origenDe(vuelo.internacional, vuelo.origen_icao ?? null)}</dd>
          </div>
          <div>
            <dt>Última verificación</dt>
            <dd>{vuelo.ultima_consulta_en ? `Con la API de vuelos el ${formatearFechaHora(vuelo.ultima_consulta_en)}` : 'Sin verificar con la API de vuelos'}</dd>
          </div>
          <div>
            <dt>Recogida sugerida</dt>
            <dd>
              {formatearHora(vuelo.recogida_sugerida, ahora)} (llegada + {vuelo.margen_min} min de margen)
            </dd>
          </div>
          <div>
            <dt>Recogida actual</dt>
            <dd>{formatearFechaHora(viaje.recogida_en)}</dd>
          </div>
        </dl>
        <PropuestaRecogida viaje={viaje} incrustada />
      </section>
    );
  }

  if (viaje.sentido === 'HACIA_AEROPUERTO' && viaje.vuelo_salida_en) {
    // Las salidas no se monitorean: sin estado ni hora estimada. El número no se registra en el viaje (DC-69).
    return (
      <section className={estilos.tarjeta} aria-labelledby="titulo-vuelo">
        <h2 id="titulo-vuelo">Vuelo de salida</h2>
        <dl className={estilos.datos}>
          <div>
            <dt>Despega</dt>
            <dd>
              {formatearFechaHora(viaje.vuelo_salida_en)}
              {tipoDeSalida(viaje)}
            </dd>
          </div>
          {viaje.en_aeropuerto_a_las && (
            <div>
              <dt>En el aeropuerto</dt>
              <dd>Debe estar en el aeropuerto a las {formatearHora(viaje.en_aeropuerto_a_las, ahora)}</dd>
            </div>
          )}
        </dl>
      </section>
    );
  }

  return null;
}
