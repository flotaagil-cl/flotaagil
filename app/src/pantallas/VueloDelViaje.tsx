import { textoSalida, textoVuelo, type VueloApp } from '../vuelo';

/** HU-69: el vuelo del viaje (llegada con estado o salida con la hora en el aeropuerto), dentro de una lista `dl`. */
export function VueloDelViaje({ vuelo, enAeropuerto }: { vuelo?: VueloApp | null; enAeropuerto?: string | null }) {
  if (vuelo) {
    const { titulo, estado, tono } = textoVuelo(vuelo);
    return (
      <>
        <dt>Vuelo</dt>
        <dd>
          {titulo} <span className={`estado-vuelo ${tono}`}>{estado}</span>
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
