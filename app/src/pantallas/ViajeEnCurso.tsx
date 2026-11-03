import { AppLauncher } from '@capacitor/app-launcher';
import { useState, type ReactNode } from 'react';
import { horaDeChile } from '../hora';
import { enlaceGoogleMaps, enlaceWaze, type ViajeActivo } from '../navegacion';

const ETAPAS = {
  ACEPTADO: 'Aceptado',
  EN_CAMINO: 'En camino',
  EN_ZONA: 'En zona',
  PASAJERO_A_BORDO: 'Pasajero a bordo',
} as const;

/**
 * Viaje en curso con los botones para navegar (HU-17): al origen hasta subir el pasajero, luego al destino. Debajo,
 * el avance del viaje (HU-16).
 */
export function ViajeEnCurso({ viaje, children }: { viaje: ViajeActivo; children?: ReactNode }) {
  const [falla, setFalla] = useState(false);
  const aBordo = viaje.estado === 'PASAJERO_A_BORDO';

  async function abrir(url: string) {
    setFalla(false);
    try {
      await AppLauncher.openUrl({ url });
    } catch {
      setFalla(true);
    }
  }

  return (
    <div className="tarjeta viaje">
      <h2>Viaje en curso · {ETAPAS[viaje.estado]}</h2>
      <dl>
        <dt>Pasajero</dt>
        <dd>{viaje.pasajero}</dd>
        <dt>Recogida</dt>
        <dd>
          {horaDeChile(viaje.recogida_en)}
          {viaje.vuelo ? ` · vuelo ${viaje.vuelo}` : ''}
        </dd>
        <dt>Origen</dt>
        <dd>{viaje.origen.direccion}</dd>
        <dt>Destino</dt>
        <dd>{viaje.destino.direccion}</dd>
      </dl>
      <p className="secundario">
        Navegar {aBordo ? 'al destino' : 'al punto de recogida'}: {viaje.hacia.direccion}
      </p>
      {falla && (
        <p className="error" role="alert">
          No se pudo abrir la navegación.
        </p>
      )}
      <div className="navegar">
        <button type="button" className="principal" onClick={() => void abrir(enlaceGoogleMaps(viaje.hacia))}>
          Google Maps
        </button>
        <button type="button" className="principal" onClick={() => void abrir(enlaceWaze(viaje.hacia))}>
          Waze
        </button>
      </div>
      {children}
    </div>
  );
}
