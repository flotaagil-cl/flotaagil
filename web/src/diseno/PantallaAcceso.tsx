import type { ReactNode } from 'react';
import { Link } from 'react-router';
import e from './diseno.module.css';
import { Icono } from './Icono';
import { Mapa } from './mapa/Mapa';
import { Insignia } from './Tarjeta';

/** Aeropuerto de Santiago (SCL), para el mapa de la pantalla de ingreso en el celular. */
const SCL = { lat: -33.393, lng: -70.794 };

interface Props {
  titulo: string;
  /** Título en el celular, si cambia (en ingresar, «Tu traslado, sin esperas»). */
  tituloMovil?: string;
  subtitulo: string;
  /**
   * En pantallas angostas: «mapa» deja el mapa arriba y el formulario en un panel (portal, bajo 900 px); «hero»
   * pone el título en una banda (portal); «centrado» oculta el panel con el degradé y centra el formulario (panel,
   * bajo 1024 px).
   */
  movil: 'mapa' | 'hero' | 'centrado';
  /** Contenido del panel con el degradé; por defecto, el del portal. */
  hero?: ReactNode;
  volver?: { a: string; texto: string };
  children: ReactNode;
}

/**
 * Ingresar, crear cuenta y las demás pantallas de acceso (HU-38). En el computador, el panel con el degradé a
 * la izquierda y el formulario a la derecha. El formulario va primero en el documento.
 */
export function PantallaAcceso({ titulo, tituloMovil, subtitulo, movil, volver, hero = <HeroPortal />, children }: Props) {
  return (
    <div className={e.acceso} data-movil={movil}>
      <div className={e.accesoFormulario}>
        <div className={e.accesoCabecera}>
          {volver && (
            <Link to={volver.a} className={e.accesoVolver} aria-label={volver.texto}>
              <Icono nombre="atras" />
            </Link>
          )}
          <h1 className={e.accesoTitulo}>
            {tituloMovil ? (
              <>
                <span className={e.soloEscritorio}>{titulo}</span>
                <span className={e.soloMovilTexto}>{tituloMovil}</span>
              </>
            ) : (
              titulo
            )}
          </h1>
          <p className={e.accesoSubtitulo}>{subtitulo}</p>
        </div>
        {children}
      </div>
      <div className={e.accesoHero}>
        <span className={e.circuloGrande} aria-hidden="true" />
        <span className={e.circuloChico} aria-hidden="true" />
        {hero}
      </div>
      {movil === 'mapa' && (
        <div className={e.accesoMapa}>
          <Mapa etiqueta="Mapa del aeropuerto de Santiago" marcadores={[{ id: 'scl', punto: SCL, tipo: 'aeropuerto', etiqueta: 'Aeropuerto de Santiago' }]} />
        </div>
      )}
    </div>
  );
}

/** Separador con texto («¿No tienes cuenta?»). */
export function Separador({ children }: { children: ReactNode }) {
  return <p className={e.separador}>{children}</p>;
}

/** Panel con el degradé del portal: la promesa al pasajero y una ilustración del seguimiento de vuelos. */
export function HeroPortal() {
  return (
    <>
      <p className={e.heroAntetitulo}>Traslados aeropuerto de Santiago</p>
      <p className={e.heroTitulo}>Tu traslado, sin esperas.</p>
      <p className={e.heroTexto}>Pides en un minuto, confirmas por WhatsApp y nosotros seguimos tu vuelo por ti.</p>
      {/* Ilustración del seguimiento de vuelos (datos de ejemplo, como en el diseño): decorativa. */}
      <div className={e.heroVuelo} aria-hidden="true">
        <div className={e.heroVueloFila}>
          <span className={e.heroVueloNumero}>Vuelo LA 845</span>
          <Insignia tono="info">Atrasado 25 min</Insignia>
        </div>
        <div className={e.heroVueloRuta}>
          <span>LIM</span>
          <span className={e.heroVueloLinea} />
          <Icono nombre="avion" tamano={18} />
          <span className={e.heroVueloLinea} />
          <span>SCL</span>
        </div>
        <span className={e.heroVueloNota}>Llega 19:05 · tu conductor ya está avisado</span>
      </div>
    </>
  );
}
