import type { ReactNode } from 'react';
import { Link } from 'react-router';
import e from './diseno.module.css';
import { Icono } from './Icono';
import { Mapa } from './mapa/Mapa';

/** Aeropuerto de Santiago (SCL), para el mapa de la pantalla de ingreso en el celular. */
const SCL = { lat: -33.393, lng: -70.794 };

interface Props {
  titulo: string;
  subtitulo: string;
  /** En el celular: «mapa» deja el mapa arriba y el formulario en un panel; «hero» pone el título en una banda. */
  movil: 'mapa' | 'hero';
  volver?: { a: string; texto: string };
  children: ReactNode;
}

/**
 * Ingresar, crear cuenta y las demás pantallas de acceso (HU-38). En el computador, el panel con el degradé a
 * la izquierda y el formulario a la derecha. El formulario va primero en el documento.
 */
export function PantallaAcceso({ titulo, subtitulo, movil, volver, children }: Props) {
  return (
    <div className={e.acceso} data-movil={movil}>
      <div className={e.accesoFormulario}>
        <div className={e.accesoCabecera}>
          {volver && (
            <Link to={volver.a} className={e.accesoVolver} aria-label={volver.texto}>
              <Icono nombre="atras" />
            </Link>
          )}
          <h1 className={e.accesoTitulo}>{titulo}</h1>
          <p className={e.accesoSubtitulo}>{subtitulo}</p>
        </div>
        {children}
      </div>
      <div className={e.accesoHero}>
        <span className={e.circuloGrande} aria-hidden="true" />
        <span className={e.circuloChico} aria-hidden="true" />
        <p className={e.heroAntetitulo}>Traslados aeropuerto de Santiago</p>
        <p className={e.heroTitulo}>Tu traslado, sin esperas.</p>
        <p className={e.heroTexto}>Pides en un minuto, confirmas por WhatsApp y nosotros seguimos tu vuelo por ti.</p>
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
