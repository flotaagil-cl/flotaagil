import { useState } from 'react';
import { Navigate, NavLink, Outlet, useLocation, useMatches, useNavigate } from 'react-router';
import { AlertasVuelo } from '../alertas/AlertasVuelo';
import { AlertasLlegada } from '../chat/AlertasLlegada';
import { ChatEnVivo } from '../chat/EnVivo';
import { NoLeidosChat } from '../chat/NoLeidos';
import { Icono } from '../diseno/Icono';
import '../diseno/tokens.css';
import { SinPermiso } from '../paginas/SinPermiso';
import { useRutas } from '../rutas/contexto';
import type { EntradaMenu, Manejo, SeccionMenu } from '../rutas/tabla';
import { entradasDeMenu, inicioDeRol, ROLES_PANEL } from '../rutas/tabla';
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
  const [menuAbierto, setMenuAbierto] = useState(false);
  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  const delPanel = ROLES_PANEL.includes(usuario.rol);
  // HU-33: el convenio y el pasajero no tienen Inicio del panel; «/» los lleva a su vista.
  if (!delPanel && pathname === '/') return <Navigate to={inicioDeRol(usuario.rol)} replace />;

  const roles = coincidencias
    .map((c) => (c.handle as Manejo | undefined)?.roles)
    .filter((r) => r !== undefined)
    .at(-1);
  const permitido = !roles || roles.includes(usuario.rol);
  const menu = entradasDeMenu(rutas, usuario.rol, '', usuario.empresa.modulo_cuentas);

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
        <NavLink to={entrada.ruta} end={entrada.ruta === '/'} onClick={() => setMenuAbierto(false)}>
          {entrada.icono && <Icono nombre={entrada.icono} tamano={18} className={estilos.iconoMenu} />}
          <span>{entrada.titulo}</span>
          {delPanel && entrada.ruta === '/chat' && <NoLeidosChat className={estilos.contadorMenu} />}
        </NavLink>
      </li>
    );
  }

  const marco = (
    <div className={`${estilos.marco} tema-flotaagil`}>
      <header className={estilos.cabecera}>
        <button
          type="button"
          className={estilos.botonMenu}
          aria-expanded={menuAbierto}
          aria-controls="menu-principal"
          onClick={() => setMenuAbierto((abierto) => !abierto)}
        >
          Menú
        </button>
        <span className={estilos.marca}>FlotaÁgil</span>
        <span className={estilos.empresa}>{usuario.empresa.razon_social}</span>
        <div className={estilos.usuario}>
          <span>
            {usuario.nombre} · {NOMBRE_ROL[usuario.rol]}
          </span>
          <button type="button" className={estilos.salir} onClick={() => void cerrarSesion()}>
            Cerrar sesión
          </button>
        </div>
      </header>
      <nav id="menu-principal" className={estilos.menu} data-abierto={menuAbierto} aria-label="Menú principal">
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
      <main className={estilos.contenido}>
        {delPanel && <AlertasVuelo />}
        {delPanel && <AlertasLlegada />}
        {permitido ? <Outlet /> : <SinPermiso />}
      </main>
    </div>
  );
  // CC-19: el canal del chat corre en todo el panel (el convenio y el pasajero no usan el chat de trabajo).
  return delPanel ? <ChatEnVivo>{marco}</ChatEnVivo> : marco;
}
