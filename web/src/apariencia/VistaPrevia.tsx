/** CC-27 (HU-78): cómo se verán el panel, el portal y la app con la paleta y el logo elegidos (decorativa). */

import { Icono } from '../diseno/Icono';
import type { ClavePaleta } from '../diseno/paletas.generado';
import panel from '../componentes/panel.module.css';
import c from './apariencia.module.css';

function Marca({ logo, empresa }: { logo: string | null; empresa: string }) {
  return logo ? (
    <span className={c.base}>
      <img src={logo} alt={`Logo de ${empresa}`} />
    </span>
  ) : (
    <span className={c.base}>
      <strong>FlotaÁgil</strong>
    </span>
  );
}

/** Los estados conservan sus colores con cualquier paleta y llevan ícono y texto. */
function Estados() {
  return (
    <span className={c.estados}>
      <span className={`${panel.etiqueta} ${panel.pendiente}`}>
        <Icono nombre="reloj" tamano={12} className={panel.iconoEtiqueta} />
        Solicitado
      </span>
      <span className={`${panel.etiqueta} ${panel.curso}`}>
        <Icono nombre="volante" tamano={12} className={panel.iconoEtiqueta} />
        En camino
      </span>
      <span className={`${panel.etiqueta} ${panel.cancelado}`}>
        <Icono nombre="cerrar" tamano={12} className={panel.iconoEtiqueta} />
        Cancelado
      </span>
    </span>
  );
}

export function VistaPrevia({ paleta, logo, empresa }: { paleta: ClavePaleta; logo: string | null; empresa: string }) {
  return (
    <div className={c.vistas} data-paleta={paleta} data-testid="vista-previa">
      <figure className={c.vista}>
        <div className={c.pantalla}>
          <div className={c.barraPanel}>
            <Marca logo={logo} empresa={empresa} />
          </div>
          <div className={c.cuerpoPanel}>
            <ul className={c.menuFalso} aria-hidden="true">
              <li data-activo="true">Reservas</li>
              <li>Mapa</li>
              <li>Conductores</li>
            </ul>
            <div className={c.contenidoFalso}>
              <span className={c.botonFalso}>Nueva reserva</span>
              <Estados />
            </div>
          </div>
        </div>
        <figcaption>Panel</figcaption>
      </figure>
      <figure className={c.vista}>
        <div className={c.pantalla}>
          <div className={c.hero}>
            <Marca logo={logo} empresa={empresa} />
            <p>¿A dónde te llevamos?</p>
          </div>
          <div className={c.contenidoFalso}>
            <span className={c.campoFalso}>Dirección de recogida</span>
            <span className={c.botonFalso}>Pedir mi traslado</span>
          </div>
        </div>
        <figcaption>Portal del pasajero</figcaption>
      </figure>
      <figure className={c.vista}>
        <div className={`${c.pantalla} ${c.telefono}`}>
          <div className={c.hero}>
            <Marca logo={logo} empresa={empresa} />
          </div>
          <div className={c.contenidoFalso}>
            <span className={c.destacadoFalso}>Viaje en curso</span>
            <span className={c.botonFalso}>Voy en camino</span>
          </div>
        </div>
        <figcaption>App del conductor</figcaption>
      </figure>
    </div>
  );
}
