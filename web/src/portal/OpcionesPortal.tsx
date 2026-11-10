import { Link } from 'react-router';
import estilos from './portal.module.css';

/**
 * HU-33: las cuatro formas de entrar al portal. Continuar como invitado es el formulario de abajo, que sigue
 * igual; las demás llevan al inicio de sesión único y a los registros de HU-34 y HU-35.
 */
export function OpcionesPortal({ slug }: { slug: string }) {
  return (
    <nav className={estilos.opciones} aria-label="Cómo quieres continuar">
      <p>
        Puedes pedir tu viaje <strong>como invitado</strong> con el formulario de abajo, o:
      </p>
      <ul>
        <li>
          <Link to={`/login?volver=${encodeURIComponent(`/solicitar/${slug}`)}`}>Iniciar sesión</Link>
        </li>
        <li>
          <Link to={`/solicitar/${slug}/cuenta`}>Crear cuenta</Link>
        </li>
        <li>
          <Link to={`/solicitar/${slug}/registro-empresa`}>Registrar mi empresa</Link>
        </li>
      </ul>
    </nav>
  );
}
