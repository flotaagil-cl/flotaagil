/** HU-69: línea de vuelo bajo una reserva de aeropuerto (listado de Reservas y «Vuelos de hoy»). */

import { Fragment } from 'react';
import { Icono } from '../diseno/Icono';
import type { EstadoDeVuelo, LineaDeVuelo } from './textos';
import c from './vuelos.module.css';

export function EstadoVuelo({ estado }: { estado: EstadoDeVuelo }) {
  return <span className={`${c.chip} ${c[estado.tono]}`}>{estado.texto}</span>;
}

export function LineaVuelo({ linea }: { linea: LineaDeVuelo }) {
  return (
    <div className={c.linea}>
      <span className={c.renglon}>
        <Icono nombre="avion" tamano={16} className={c.icono} />
        <span>{linea.principal}</span>
        {linea.estado && <EstadoVuelo estado={linea.estado} />}
      </span>
      {linea.detalle.length > 0 && (
        <span className={`${c.renglon} ${c.detalle}`}>
          {linea.detalle.map((parte, i) => (
            <Fragment key={parte}>
              {i > 0 && <span className={c.separador} aria-hidden="true">·</span>}
              <span className={parte.startsWith('⚠') ? c.aviso : undefined}>{parte}</span>
            </Fragment>
          ))}
        </span>
      )}
    </div>
  );
}
