import { useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';
import estilos from './Login.module.css';

const MINIMO = 10;

/**
 * DC-40: primer ingreso con contraseña temporal (DC-14) para todos los roles web. La API responde 403
 * `cambio_password_requerido` en todo salvo cambiar la contraseña, así que la guarda de rutas trae aquí a quien
 * tenga `debe_cambiar_password`. Al cambiarla, se vuelve a iniciar sesión con la nueva y se sigue a su vista.
 */
export function PrimerIngreso() {
  const { sesion, estado } = useSesion();
  const api = useApi();
  const navegar = useNavigate();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  if (!usuario.debe_cambiar_password) return <Navigate to={inicioDeRol(usuario.rol)} replace />;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const e: Record<string, string> = {};
    if (!actual) e.actual = 'Ingresa la contraseña temporal.';
    if (nueva.length < MINIMO) e.nueva = `Mínimo ${MINIMO} caracteres.`;
    else if (nueva === actual) e.nueva = 'Debe ser distinta de la temporal.';
    if (repetida !== nueva) e.repetida = 'Las contraseñas no coinciden.';
    setErrores(e);
    setFalla(null);
    if (Object.keys(e).length) return;
    setEnviando(true);
    try {
      await resultado(api.POST('/api/auth/password/', { body: { password_actual: actual, password_nueva: nueva } }));
      const entrada = await sesion.login(usuario.email, nueva);
      if (!entrada.ok) {
        navegar('/login', { replace: true });
        return;
      }
      navegar(inicioDeRol(usuario.rol), { replace: true });
    } catch (error) {
      const cuerpo = error instanceof ErrorApi ? ((error.cuerpo ?? {}) as Record<string, string[] | undefined>) : {};
      if (cuerpo.password_actual?.[0] || cuerpo.password_nueva?.[0]) {
        setErrores({
          ...(cuerpo.password_actual?.[0] && { actual: cuerpo.password_actual[0] }),
          ...(cuerpo.password_nueva?.[0] && { nueva: cuerpo.password_nueva[0] }),
        });
      } else {
        setFalla('No se pudo cambiar la contraseña. Intenta de nuevo.');
      }
    } finally {
      setEnviando(false);
    }
  }

  const campo = (id: string, etiqueta: string, valor: string, cambiar: (v: string) => void, autocompletar: string) => (
    <div className={estilos.campo}>
      <label htmlFor={`primer-${id}`}>{etiqueta}</label>
      <input
        id={`primer-${id}`}
        type="password"
        autoComplete={autocompletar}
        value={valor}
        aria-invalid={errores[id] ? true : undefined}
        aria-describedby={errores[id] ? `primer-${id}-error` : undefined}
        onChange={(evento) => cambiar(evento.target.value)}
      />
      {errores[id] && (
        <span id={`primer-${id}-error`} className={estilos.errorCampo}>
          {errores[id]}
        </span>
      )}
    </div>
  );

  return (
    <main className={estilos.pagina}>
      <form className={estilos.tarjeta} onSubmit={(evento) => void enviar(evento)} noValidate aria-labelledby="titulo-primer-ingreso">
        <h1 id="titulo-primer-ingreso">
          <span className={estilos.marca}>FlotaÁgil</span> Crea tu contraseña
        </h1>
        <p>
          Hola, {usuario.nombre}. Entraste con una contraseña temporal: elige una propia para seguir.
        </p>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        {campo('actual', 'Contraseña temporal', actual, setActual, 'current-password')}
        {campo('nueva', 'Contraseña nueva', nueva, setNueva, 'new-password')}
        {campo('repetida', 'Repite la contraseña nueva', repetida, setRepetida, 'new-password')}
        <p>Al menos {MINIMO} caracteres, distinta de la temporal.</p>
        <button type="submit" className={estilos.boton} disabled={enviando}>
          {enviando ? 'Guardando…' : 'Guardar y continuar'}
        </button>
        <button type="button" className={estilos.boton} onClick={() => void sesion.logout().then(() => navegar('/login', { replace: true }))}>
          Cerrar sesión
        </button>
      </form>
    </main>
  );
}
