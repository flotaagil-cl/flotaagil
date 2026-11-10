import { useMemo, useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router';
import { ErrorApi } from '../api/resultado';
import { useEntorno } from '../entornoContexto';
import { crearClientePortal } from '../portal/api';
import estilos from '../paginas/Login.module.css';

/** HU-35: sin sesión, con el cliente público (no carga nada de la sesión del panel). */
function useClientePublico() {
  const entorno = useEntorno();
  return useMemo(() => crearClientePortal(entorno), [entorno]);
}

async function sinCuerpo(llamada: Promise<{ response: Response; error?: unknown }>) {
  let respuesta: Awaited<typeof llamada>;
  try {
    respuesta = await llamada;
  } catch {
    throw new ErrorApi(0, null);
  }
  if (!respuesta.response.ok) throw new ErrorApi(respuesta.response.status, respuesta.error ?? null);
}

/** Pide el enlace. Responde lo mismo exista o no el correo. */
export function Recuperar() {
  const api = useClientePublico();
  const [email, setEmail] = useState('');
  const [enviado, setEnviado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setError('Ingresa un correo válido.');
      return;
    }
    setEnviando(true);
    try {
      await sinCuerpo(api.POST('/api/auth/recuperar/', { body: { email } }));
      setEnviado(true);
    } catch (falla) {
      setError(falla instanceof ErrorApi && falla.estado === 429 ? 'Demasiados intentos. Espera un momento.' : 'No se pudo enviar. Intenta de nuevo.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <main className={estilos.pagina}>
      <form className={estilos.tarjeta} onSubmit={(e) => void enviar(e)} noValidate>
        <h1>Recuperar la contraseña</h1>
        {enviado ? (
          <p role="status">Si el correo tiene una cuenta de pasajero o de convenio, te enviamos un enlace para elegir una contraseña nueva.</p>
        ) : (
          <>
            {error && <p role="alert">{error}</p>}
            <label className={estilos.campo}>
              Correo
              <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
            </label>
            <button type="submit" disabled={enviando}>
              {enviando ? 'Enviando…' : 'Enviar enlace'}
            </button>
          </>
        )}
        <p>
          <Link to="/login">Volver a iniciar sesión</Link>
        </p>
      </form>
    </main>
  );
}

/** Elige la contraseña nueva con el enlace del correo. */
export function ElegirPassword() {
  const { uid = '', token = '' } = useParams();
  const api = useClientePublico();
  const [password, setPassword] = useState('');
  const [listo, setListo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardando, setGuardando] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    if (password.length < 10) {
      setError('Mínimo 10 caracteres.');
      return;
    }
    setGuardando(true);
    try {
      await sinCuerpo(api.POST('/api/auth/recuperar/confirmar/', { body: { uid, token, password } }));
      setListo(true);
    } catch (falla) {
      const cuerpo = falla instanceof ErrorApi ? ((falla.cuerpo ?? {}) as Record<string, string[] | undefined>) : {};
      setError(cuerpo.token?.[0] ?? cuerpo.password?.[0] ?? 'No se pudo cambiar la contraseña.');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <main className={estilos.pagina}>
      <form className={estilos.tarjeta} onSubmit={(e) => void enviar(e)} noValidate>
        <h1>Elegir una contraseña nueva</h1>
        {listo ? (
          <p role="status">Listo. Ya puedes iniciar sesión con tu contraseña nueva.</p>
        ) : (
          <>
            {error && <p role="alert">{error}</p>}
            <label className={estilos.campo}>
              Contraseña nueva
              <input type="password" autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            <button type="submit" disabled={guardando}>
              {guardando ? 'Guardando…' : 'Guardar'}
            </button>
          </>
        )}
        <p>
          <Link to="/login">Ir a iniciar sesión</Link>
        </p>
      </form>
    </main>
  );
}
