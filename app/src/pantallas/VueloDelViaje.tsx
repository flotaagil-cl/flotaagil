import { Icono } from '../componentes/Icono';
import { textoSalida, textoVuelo, type VueloApp } from '../vuelo';

const ICONO_TONO = { ok: 'check', aviso: 'reloj', error: 'alerta', neutro: 'check' } as const;

/** HU-69: el vuelo del viaje (llegada con estado o salida con la hora en el aeropuerto), dentro de una lista `dl`. */
export function VueloDelViaje({ vuelo, enAeropuerto }: { vuelo?: VueloApp | null; enAeropuerto?: string | null }) {
  if (vuelo) {
    const { titulo, estado, tono } = textoVuelo(vuelo);
    return (
      <>
        <dt>Vuelo</dt>
        <dd>
          {titulo}{' '}
          <span className={`estado-vuelo ${tono}`}>
            <Icono nombre={ICONO_TONO[tono]} tamano={13} />
            {estado}
          </span>
        </dd>
      </>
    );
  }
  if (enAeropuerto) {
    return (
      <>
        <dt>Aeropuerto</dt>
        <dd>{textoSalida(enAeropuerto)}</dd>
      </>
    );
  }
  return null;
}
