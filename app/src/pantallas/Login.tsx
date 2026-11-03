import { useState, type FormEvent } from 'react';
import { ErrorApi, SinRed, type SesionApp } from '../sesion/sesion';

const MENSAJES: Record<string, string> = {
  credenciales_invalidas: 'Correo o contraseña incorrectos.',
  cuenta_bloqueada: 'Tu cuenta está bloqueada por intentos fallidos. Intenta más tarde.',
  cuenta_deshabilitada: 'Tu cuenta está deshabilitada. Habla con el administrador de tu empresa.',
  password_temporal_vencida: 'Tu contraseña temporal venció. Pide una nueva al administrador de tu empresa.',
  rol_no_permitido: 'Esta app es solo para conductores. El panel se usa desde el navegador.',
  throttled: 'Demasiados intentos. Espera un momento.',
};

function mensaje(error: unknown): string {
  if (error instanceof SinRed) return 'No se pudo conectar con el servidor. Revisa tu conexión.';
  if (error instanceof ErrorApi) return (error.codigo && MENSAJES[error.codigo]) || 'Revisa el correo y la contraseña.';
  return 'Ocurrió un error inesperado. Intenta de nuevo.';
}

export function Login({ sesion, motivo }: { sesion: SesionApp; motivo?: string }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function ingresar(evento: FormEvent) {
    evento.preventDefault();
    setFalla(null);
    setEnviando(true);
    try {
      await sesion.login(email.trim(), password);
    } catch (error) {
      setFalla(mensaje(error));
      setEnviando(false);
    }
  }

  return (
    <main>
      <h1>FlotaÁgil Conductor</h1>
      {motivo === 'sesion_terminada' && <p className="aviso">Tu sesión terminó. Ingresa de nuevo.</p>}
      {motivo === 'sin_conexion' && (
        <p className="aviso">
          Sin conexión con el servidor.{' '}
          <button type="button" onClick={() => void sesion.iniciar()}>
            Reintentar
          </button>
        </p>
      )}
      {falla && (
        <p className="error" role="alert">
          {falla}
        </p>
      )}
      <form onSubmit={ingresar} noValidate>
        <label>
          Correo
          <input type="email" autoComplete="username" inputMode="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </label>
        <label>
          Contraseña
          <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </label>
        <button className="principal" type="submit" disabled={enviando || !email || !password}>
          {enviando ? 'Ingresando…' : 'Ingresar'}
        </button>
      </form>
    </main>
  );
}
