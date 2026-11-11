import e from './diseno.module.css';
import { Icono } from './Icono';

export type EstadoPaso = 'hecho' | 'actual' | 'pendiente';

export interface PasoLinea {
  titulo: string;
  detalle?: string;
  estado: EstadoPaso;
}

const LEIDO: Record<EstadoPaso, string> = { hecho: 'listo', actual: 'en curso', pendiente: 'pendiente' };

/** Avance de un viaje. El paso en curso lleva aria-current="step" y cada paso dice su estado en texto. */
export function LineaDeTiempo({ etiqueta, pasos }: { etiqueta: string; pasos: PasoLinea[] }) {
  return (
    <ol className={e.linea} aria-label={etiqueta}>
      {pasos.map((paso) => (
        <li key={paso.titulo} className={e.paso} data-estado={paso.estado} aria-current={paso.estado === 'actual' ? 'step' : undefined}>
          <span className={e.marcaPaso} aria-hidden="true">
            {paso.estado === 'hecho' && <Icono nombre="check" tamano={14} />}
          </span>
          <span className={e.textoPaso}>
            <span className={e.tituloPaso}>
              {paso.titulo}
              <span className="solo-lector"> ({LEIDO[paso.estado]})</span>
            </span>
            {paso.detalle && <span className={e.detallePaso}>{paso.detalle}</span>}
          </span>
        </li>
      ))}
    </ol>
  );
}
