import { Icono } from '../../diseno/Icono';
import { formatearFechaHora } from '../../hora/hora';
import type { Viaje } from '../api';
import d from './DialogosReserva.module.css';

export function CabeceraDialogo({
  tituloId,
  titulo,
  alCerrar,
  deshabilitado,
}: {
  tituloId: string;
  titulo: string;
  alCerrar: () => void;
  deshabilitado?: boolean;
}) {
  return (
    <div className={d.cabecera}>
      <h2 id={tituloId}>{titulo}</h2>
      <button type="button" className={d.botonCerrar} aria-label="Cerrar" onClick={alCerrar} disabled={deshabilitado}>
        <Icono nombre="cerrar" tamano={16} />
      </button>
    </div>
  );
}

/** Ficha compacta del viaje compartida por los diálogos de asignación, cancelación y cierre forzado. */
export function ResumenViajeDialogo({ viaje, conductorNombre }: { viaje: Viaje; conductorNombre?: string }) {
  return (
    <div className={d.resumenViaje}>
      <div className={d.resumenSuperior}>
        <span className={d.pasajero}>
          {viaje.pasajero.nombre}
          {conductorNombre ? ` · ${conductorNombre}` : ''}
        </span>
        <span className={d.horaBadge}>
          <Icono nombre="reloj" tamano={13} aria-hidden="true" />
          Recogida {formatearFechaHora(viaje.recogida_en)}
        </span>
      </div>
      <p className={d.trayecto}>
        {viaje.origen.direccion} → {viaje.destino.direccion}
      </p>
    </div>
  );
}
