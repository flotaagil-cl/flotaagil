import { useMemo } from 'react';
import { mapaDeDirecciones, type Coordenadas, type TipoDeViaje } from './direcciones';
import { Mapa } from './Mapa';
import e from './MapaDirecciones.module.css';

interface Props {
  tipo: TipoDeViaje | null;
  origen?: Coordenadas | null;
  destino?: Coordenadas | null;
  /** Mapa chico bajo las direcciones. Sin esto llena su contenedor (el mapa al costado de /pedir). */
  chico?: boolean;
}

/** HU-71: el punto elegido en las direcciones, sobre el mapa del portal (OpenStreetMap con respaldo, DC-71). */
export function MapaDirecciones({ tipo, origen, destino, chico = false }: Props) {
  const [latO, lonO, latD, lonD] = [origen?.lat, origen?.lon, destino?.lat, destino?.lon];
  // Solo cambia con los puntos: si no, el mapa volvería a encuadrar en cada tecla.
  const props = useMemo(
    () =>
      mapaDeDirecciones(
        tipo,
        latO === undefined || lonO === undefined ? null : { lat: latO, lon: lonO },
        latD === undefined || lonD === undefined ? null : { lat: latD, lon: lonD },
      ),
    [tipo, latO, lonO, latD, lonD],
  );
  if (!chico) return <Mapa {...props} />;
  return (
    <div className={e.chico}>
      <Mapa {...props} />
    </div>
  );
}
