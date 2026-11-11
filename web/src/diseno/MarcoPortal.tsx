import { useState, type CSSProperties, type ReactNode } from 'react';
import { Link, NavLink } from 'react-router';
import { iniciales } from './clases';
import e from './diseno.module.css';
import { Dialogo } from './Dialogo';
import { Icono } from './Icono';
import { Avatar } from './Tarjeta';

export interface EnlacePortal {
  a: string;
  texto: string;
}

interface Props {
  /** Nombre de la empresa de taxis (razón social). */
  marca: string;
  /** Adónde lleva la marca. */
  inicio?: string;
  enlaces?: EnlacePortal[];
  usuario?: { nombre: string } | null;
  onCerrarSesion?: () => void;
  /** En el celular: «flotante» deja la barra sobre el mapa; «oculta» la saca (pantallas con volver). */
  barraMovil?: 'normal' | 'flotante' | 'oculta';
  /** Color por empresa (más adelante): tokens de marca que reemplazan a los del portal. */
  colores?: Partial<Record<'--color-primario-900' | '--color-primario-700' | '--color-tiffany', string>>;
  /** Enlace a la derecha de la barra cuando no hay sesión («¿Eres empresa? Registra tu convenio»). */
  accion?: EnlacePortal;
  /** Pie de página (aviso de privacidad). */
  pie?: ReactNode;
  children: ReactNode;
}

/**
 * Marco del portal (HU-37): barra superior con la marca, la navegación y la cuenta. En el celular la
 * navegación pasa al menú de la cuenta (diálogo), que también tiene «Cerrar sesión».
 */
export function MarcoPortal({ marca, inicio = '/', enlaces = [], usuario, onCerrarSesion, barraMovil = 'normal', colores, accion, pie, children }: Props) {
  const [menu, setMenu] = useState(false);
  return (
    <div className={`tema-portal ${e.marco}`} style={colores as CSSProperties | undefined}>
      <a href="#contenido" className={e.saltar}>
        Saltar al contenido
      </a>
      <header className={e.barra} data-movil={barraMovil}>
        <Link to={inicio} className={e.marca}>
          <span className={e.logo} aria-hidden="true">
            {iniciales(marca)}
          </span>
          <span className={e.marcaNombre}>{marca}</span>
        </Link>
        {enlaces.length > 0 && (
          <nav aria-label="Principal" className={e.nav}>
            {enlaces.map((enlace) => (
              <NavLink key={enlace.a} to={enlace.a} className={e.navEnlace} end>
                {enlace.texto}
              </NavLink>
            ))}
          </nav>
        )}
        {accion && !usuario && (
          <Link to={accion.a} className={e.accion}>
            {accion.texto}
          </Link>
        )}
        {usuario && (
          <button type="button" className={e.botonCuenta} aria-haspopup="dialog" aria-expanded={menu} onClick={() => setMenu(true)}>
            <Avatar texto={iniciales(usuario.nombre)} />
            <span className={e.nombreUsuario}>{usuario.nombre}</span>
            <span className="solo-lector">: menú de la cuenta</span>
          </button>
        )}
      </header>
      <Dialogo abierto={menu} titulo="Tu cuenta" variante="menu" onCerrar={() => setMenu(false)}>
        <nav aria-label="Cuenta" className={e.menuCuenta}>
          {enlaces.map((enlace) => (
            <Link key={enlace.a} to={enlace.a} className={e.menuEnlace} onClick={() => setMenu(false)}>
              {enlace.texto}
              <Icono nombre="derecha" tamano={18} />
            </Link>
          ))}
          {onCerrarSesion && (
            <button
              type="button"
              className={e.menuEnlace}
              onClick={() => {
                setMenu(false);
                onCerrarSesion();
              }}
            >
              Cerrar sesión
              <Icono nombre="salir" tamano={18} />
            </button>
          )}
        </nav>
      </Dialogo>
      <main id="contenido" tabIndex={-1} className={e.contenido}>
        {children}
      </main>
      {pie && <footer className={e.pie}>{pie}</footer>}
    </div>
  );
}
