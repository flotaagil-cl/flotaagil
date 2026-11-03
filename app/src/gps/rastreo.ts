import type {
  BackgroundGeolocationPlugin,
  CallbackError,
  Location,
} from '@capacitor-community/background-geolocation';
import { registerPlugin } from '@capacitor/core';

const BackgroundGeolocation = registerPlugin<BackgroundGeolocationPlugin>('BackgroundGeolocation');

/**
 * Inicia el servicio de ubicación en primer plano (notificación fija en Android mientras dure el turno).
 * distanceFilter 0: el plugin entrega posiciones aunque el teléfono esté quieto (H-3).
 */
export function iniciarRastreo(
  alRecibir: (posicion: Location) => void,
  alFallar: (error: CallbackError) => void,
): Promise<string> {
  return BackgroundGeolocation.addWatcher(
    {
      backgroundTitle: 'FlotaÁgil: en turno',
      backgroundMessage: 'Se registra tu ubicación mientras estés en turno. Para detenerlo, pasa a No disponible.',
      requestPermissions: true,
      stale: false,
      distanceFilter: 0,
    },
    (posicion, error) => {
      if (error) alFallar(error);
      else if (posicion) alRecibir(posicion);
    },
  );
}

export const detenerRastreo = (id: string) => BackgroundGeolocation.removeWatcher({ id });

export const abrirAjustes = () => BackgroundGeolocation.openSettings();

export type { CallbackError, Location };
