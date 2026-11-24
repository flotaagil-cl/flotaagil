import { AppLauncher } from '@capacitor/app-launcher';
import { useState, type ReactNode } from 'react';
import { Icono } from '../componentes/Icono';
import { horaDeChile } from '../hora';
import { enlaceGoogleMaps, enlaceWaze, type ViajeActivo } from '../navegacion';
import { VueloDelViaje } from './VueloDelViaje';

const ETAPAS = {
  ACEPTADO: 'Aceptado',
  EN_CAMINO: 'En camino',
  EN_ZONA: 'En zona',
  PASAJERO_A_BORDO: 'Pasajero a bordo',
} as const;

const PASOS_BARRA = [
  { etiqueta: 'En camino', minimo: 0 },
  { etiqueta: 'En zona', minimo: 1 },
  { etiqueta: 'A bordo', minimo: 2 },
  { etiqueta: 'Finalizado', minimo: 3 },
] as const;

function indicePaso(estado: ViajeActivo['estado']): number {
  if (estado === 'PASAJERO_A_BORDO') return 2;
  if (estado === 'EN_ZONA') return 1;
  return 0;
}

/**
 * Viaje en curso con barra de 4 etapas y botones para navegar (HU-17): al origen hasta subir el pasajero,
 * luego al destino. Debajo, el avance del viaje (HU-16).
 */
export function ViajeEnCurso({ viaje, children }: { viaje: ViajeActivo; children?: ReactNode }) {
  const [falla, setFalla] = useState(false);
  const aBordo = viaje.estado === 'PASAJERO_A_BORDO';
  const pasoActual = indicePaso(viaje.estado);

  async function abrir(url: string) {
    setFalla(false);
    try {
      await AppLauncher.openUrl({ url });
    } catch {
      setFalla(true);
    }
  }

  return (
    <section className="tarjeta viaje prioritaria">
      <div className="viaje-pasos" aria-hidden="true">
        {PASOS_BARRA.map((paso) => (
          <div key={paso.etiqueta} className={pasoActual >= paso.minimo ? 'viaje-paso activo' : 'viaje-paso'}>
            <span className="viaje-paso-barra" />
            <span className="viaje-paso-texto">{paso.etiqueta}</span>
          </div>
        ))}
      </div>

      <h2>Viaje en curso · {ETAPAS[viaje.estado]}</h2>

      <dl className="lista-datos viaje-datos">
        <dt>Pasajero</dt>
        <dd>{viaje.pasajero}</dd>
        {viaje.acompanantes && viaje.acompanantes.length > 0 && (
          <>
            <dt>Acompañantes</dt>
            <dd>{viaje.acompanantes.join(', ')}</dd>
          </>
        )}
        <dt>Recogida</dt>
        <dd>
          {horaDeChile(viaje.recogida_en)}
          {viaje.vuelo && !viaje.detalle_vuelo ? ` · vuelo ${viaje.vuelo}` : ''}
        </dd>
        {/* HU-69: el estado del vuelo se renueva con el viaje (App recarga cada minuto mientras haya vuelo). */}
        {!aBordo && <VueloDelViaje vuelo={viaje.detalle_vuelo} enAeropuerto={viaje.en_aeropuerto_a_las} />}
        <dt>Origen</dt>
        <dd>{viaje.origen.direccion}</dd>
        <dt>Destino</dt>
        <dd>{viaje.destino.direccion}</dd>
      </dl>

      <div className="viaje-destino-barra">
        <Icono nombre="ubicacion" tamano={18} />
        <p className="secundario">
          Navegar {aBordo ? 'al destino' : 'al punto de recogida'}: <strong>{viaje.hacia.direccion}</strong>
        </p>
      </div>

      {falla && (
        <p className="error alerta-bloque" role="alert">
          <Icono nombre="alerta" tamano={18} />
          <span>No se pudo abrir la navegación.</span>
        </p>
      )}

      <div className="navegar">
        <button type="button" className="principal boton-navegar" onClick={() => void abrir(enlaceGoogleMaps(viaje.hacia, viaje.navegar_con))}>
          Google Maps
        </button>
        <button type="button" className="principal secundaria boton-navegar" onClick={() => void abrir(enlaceWaze(viaje.hacia, viaje.navegar_con))}>
          Waze
        </button>
      </div>
      {children}
    </section>
  );
}
