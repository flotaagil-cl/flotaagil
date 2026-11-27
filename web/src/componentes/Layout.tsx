import { useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Outlet, useLocation, useMatches, useNavigate } from 'react-router';
import { AlertasVuelo } from '../alertas/AlertasVuelo';
import { AlertasLlegada } from '../chat/AlertasLlegada';
import { ChatEnVivo } from '../chat/EnVivo';
import { NoLeidosChat } from '../chat/NoLeidos';
import { iniciales } from '../diseno/clases';
import { Icono } from '../diseno/Icono';
import { formatearTitulo } from '../diseno/titulo';
import '../diseno/tokens.css';
import '../diseno/paletas.css';
import { LogoEmpresa } from '../diseno/LogoEmpresa';
import { nombreVisible } from '../diseno/marca';
import { SinPermiso } from '../paginas/SinPermiso';
import { useRutas } from '../rutas/contexto';
import type { EntradaMenu, Manejo, SeccionMenu } from '../rutas/tabla';
import { entradasDeMenu, inicioDeRol, ROLES_PANEL, tieneModulo } from '../rutas/tabla';
import { useSesion } from '../sesion/SesionProvider';
import estilos from './Layout.module.css';

const NOMBRE_ROL = {
  ADMINISTRADOR: 'Administrador',
  DESPACHADOR: 'Despachador',
  CONDUCTOR: 'Conductor',
  CONVENIO: 'Empresa con convenio',
  PASAJERO: 'Pasajero',
};

const SECCIONES: { clave: SeccionMenu; titulo: string }[] = [
  { clave: 'operacion', titulo: 'Operación' },
  { clave: 'flota', titulo: 'Flota y clientes' },
  { clave: 'administracion', titulo: 'Administración' },
];

/** Marco del panel: cabecera, menú agrupado por rol y guarda por rol (solo UX: el backend responde 403 igual). */
export function Layout() {
  const { sesion, estado } = useSesion();
  const rutas = useRutas();
  const coincidencias = useMatches();
  const navegar = useNavigate();
  const { pathname } = useLocation();
  const [rutaMenuAbierto, setRutaMenuAbierto] = useState<string | null>(null);
  const menuAbierto = rutaMenuAbierto === pathname;
  const botonMenuRef = useRef<HTMLButtonElement>(null);
  const autenticado = estado.fase === 'autenticada';
  const roles = coincidencias
    .map((c) => (c.handle as Manejo | undefined)?.roles)
    .filter((r) => r !== undefined)
    .at(-1);
  const permitido = autenticado ? !roles || roles.includes(estado.usuario.rol) : true;
  const tituloRuta = coincidencias
    .map((c) => (c.handle as Manejo | undefined)?.titulo)
    .filter((t): t is string => Boolean(t))
    .at(-1);

  useEffect(() => {
    if (autenticado && tituloRuta) {
      document.title = formatearTitulo(!permitido ? 'Sin permiso' : tituloRuta);
    }
  }, [autenticado, permitido, tituloRuta]);

  useEffect(() => {
    if (!menuAbierto) return;
    function alPresionar(evento: KeyboardEvent) {
      if (evento.key === 'Escape') {
        setRutaMenuAbierto(null);
        botonMenuRef.current?.focus();
      }
    }
    window.addEventListener('keydown', alPresionar);
    return () => window.removeEventListener('keydown', alPresionar);
  }, [menuAbierto]);

  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  const empresaVisible = nombreVisible(usuario.empresa.apariencia, usuario.empresa.razon_social);
  const inicialesUsuario = iniciales(usuario.nombre);
  const delPanel = ROLES_PANEL.includes(usuario.rol);
  // HU-33: el convenio y el pasajero no tienen Inicio del panel; «/» los lleva a su vista.
  if (!delPanel && pathname === '/') return <Navigate to={inicioDeRol(usuario.rol)} replace />;
  // HU-75 (DC-79): el módulo de la pantalla (de la ruta o de su sección); el backend responde 403 igual.
  const modulo = coincidencias
    .map((c) => (c.handle as Manejo | undefined)?.modulo)
    .filter((m) => m !== undefined)
    .at(0);
  const conElModulo = tieneModulo(usuario.modulos, modulo);
  const usaChat = tieneModulo(usuario.modulos, 'CHAT');
  const menu = entradasDeMenu(rutas, usuario.rol, '', usuario.empresa.modulo_cuentas, delPanel ? usuario.modulos : undefined);

  const grupos = SECCIONES.map((s) => ({
    ...s,
    entradas: menu.filter((e) => e.seccion === s.clave),
  })).filter((g) => g.entradas.length > 0);
  const sinSeccion = menu.filter((e) => !e.seccion);

  async function cerrarSesion() {
    await sesion.logout();
    navegar('/login', { replace: true });
  }

  function renderEnlace(entrada: EntradaMenu) {
    return (
      <li key={entrada.ruta}>
        {/* Inicio solo se marca en «/»; Reservas también en /reservas/42. */}
        <NavLink to={entrada.ruta} end={entrada.ruta === '/'} onClick={() => setRutaMenuAbierto(null)}>
          {entrada.icono && <Icono nombre={entrada.icono} tamano={18} className={estilos.iconoMenu} />}
          <span>{entrada.titulo}</span>
          {delPanel && usaChat && entrada.ruta === '/chat' && <NoLeidosChat className={estilos.contadorMenu} />}
        </NavLink>
      </li>
    );
  }

  const marco = (
    // CC-27: la paleta de la empresa reemplaza los tokens de marca; al guardar en «Apariencia» cambia sin recargar.
    <div className={`${estilos.marco} tema-flotaagil`} data-paleta={usuario.empresa.apariencia?.paleta}>
      <header className={estilos.cabecera}>
        <button
          ref={botonMenuRef}
          type="button"
          className={estilos.botonMenu}
          aria-expanded={menuAbierto}
          aria-controls="lateral-panel"
          onClick={() => setRutaMenuAbierto((anterior) => (anterior === pathname ? null : pathname))}
        >
          <Icono nombre="lista" tamano={18} />
          <span>Menú</span>
        </button>
        <div className={estilos.identidad}>
          <LogoEmpresa
            apariencia={usuario.empresa.apariencia}
            variante="panel"
            empresa={empresaVisible}
            respaldo={<span className={estilos.marca}>FlotaÁgil</span>}
          />
          <span className={estilos.empresa} title={empresaVisible}>
            {empresaVisible}
          </span>
        </div>
        <div className={estilos.usuario}>
          <span className={estilos.avatar} aria-hidden="true">
            {inicialesUsuario}
          </span>
          <span className={estilos.nombreUsuario}>{usuario.nombre}</span>
          <span className={estilos.rolInsignia}>{NOMBRE_ROL[usuario.rol]}</span>
        </div>
      </header>
      {menuAbierto && <div className={estilos.telon} aria-hidden="true" onClick={() => setRutaMenuAbierto(null)} />}
      <aside id="lateral-panel" className={estilos.lateral} data-abierto={menuAbierto}>
        <div className={estilos.cabeceraLateral}>
          <span className={estilos.tituloLateral}>Navegación</span>
          <button type="button" className={estilos.cerrarLateral} aria-label="Cerrar menú" onClick={() => setRutaMenuAbierto(null)}>
            <Icono nombre="cerrar" tamano={18} />
          </button>
        </div>
        <nav id="menu-principal" className={estilos.menu} aria-label="Menú principal">
          {grupos.map((grupo) => (
            <div key={grupo.clave} className={estilos.grupoMenu} role="group" aria-labelledby={`menu-seccion-${grupo.clave}`}>
              <p id={`menu-seccion-${grupo.clave}`} className={estilos.tituloGrupo}>
                {grupo.titulo}
              </p>
              <ul>{grupo.entradas.map(renderEnlace)}</ul>
            </div>
          ))}
          {sinSeccion.length > 0 && <ul>{sinSeccion.map(renderEnlace)}</ul>}
        </nav>
        <div className={estilos.pieLateral}>
          <div className={estilos.perfilLateral}>
            <span className={estilos.avatar} aria-hidden="true">
              {inicialesUsuario}
            </span>
            <div className={estilos.datosPerfil}>
              <span className={estilos.nombrePerfil}>{usuario.nombre}</span>
              <span className={estilos.rolPerfil}>{NOMBRE_ROL[usuario.rol]}</span>
            </div>
          </div>
          <button type="button" className={estilos.salir} onClick={() => void cerrarSesion()}>
            <Icono nombre="salir" tamano={16} />
            <span>Cerrar sesión</span>
          </button>
        </div>
      </aside>
      <div className={estilos.principal}>
        <main className={estilos.contenido}>
          {delPanel && tieneModulo(usuario.modulos, 'RESERVAS') && <AlertasVuelo />}
          {delPanel && usaChat && <AlertasLlegada />}
          {!permitido ? (
            <SinPermiso />
          ) : conElModulo ? (
            <Outlet />
          ) : (
            // HU-75: un módulo apagado (p. ej., un enlace viejo) lleva a Inicio con el aviso.
            <Navigate to="/" replace state={{ aviso: 'No tienes acceso a este módulo. Pídeselo al administrador.' }} />
          )}
        </main>
        <footer className={estilos.piePanel}>
          <span>FlotaÁgil · Panel de operación</span>
          <span>{usuario.empresa.razon_social}</span>
        </footer>
      </div>
    </div>
  );
  // CC-19: el canal del chat corre en todo el panel (el convenio y el pasajero no usan el chat de trabajo).
  // HU-75: salvo para el despachador sin el módulo Chat.
  return delPanel && usaChat ? <ChatEnVivo>{marco}</ChatEnVivo> : marco;
}
