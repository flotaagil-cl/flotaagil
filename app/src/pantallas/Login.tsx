import { useState, type FormEvent } from 'react';
import { Icono } from '../componentes/Icono';
import { Marca } from '../componentes/Marca';
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

/** Pantalla de ingreso de la app del conductor con el sistema visual de FlotaÁgil. */
export function Login({ sesion, motivo }: { sesion: SesionApp; motivo?: string }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mostrarClave, setMostrarClave] = useState(false);
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
    <main className="login-pantalla">
      <header className="login-hero">
        <span className="login-circulo-grande" aria-hidden="true" />
        <span className="login-circulo-chico" aria-hidden="true" />
        <Marca clase="login-logo" tamano={34} />
        <h1>FlotaÁgil</h1>
        <p className="login-subtitulo">App del conductor</p>
      </header>

      <section className="login-panel">
        <div className="login-contenido">
          <h2 className="login-titulo-form">Iniciar sesión</h2>
          <p className="login-bajada">Ingresa con tu cuenta de conductor.</p>

          {motivo === 'sesion_terminada' && (
            <p className="aviso login-alerta">
              <Icono nombre="alerta" tamano={18} />
              <span>Tu sesión terminó. Ingresa de nuevo.</span>
            </p>
          )}
          {motivo === 'sin_conexion' && (
            <p className="aviso login-alerta">
              <Icono nombre="alerta" tamano={18} />
              <span>
                Sin conexión con el servidor.{' '}
                <button className="login-reintentar" type="button" onClick={() => void sesion.iniciar()}>
                  Reintentar
                </button>
              </span>
            </p>
          )}
          {falla && (
            <p className="error login-alerta" role="alert">
              <Icono nombre="alerta" tamano={18} />
              <span>{falla}</span>
            </p>
          )}

          <form className="login-formulario" onSubmit={ingresar} noValidate>
            <div className="login-campo">
              <label htmlFor="login-correo">Correo</label>
              <div className="campo-entrada">
                <Icono nombre="correo" tamano={18} className="campo-entrada-icono" />
                <input
                  id="login-correo"
                  type="email"
                  placeholder="nombre@empresa.cl"
                  autoComplete="username"
                  autoCapitalize="none"
                  autoCorrect="off"
                  spellCheck={false}
                  inputMode="email"
                  enterKeyHint="next"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="login-campo">
              <label htmlFor="login-clave">Contraseña</label>
              <div className="campo-entrada">
                <Icono nombre="candado" tamano={18} className="campo-entrada-icono" />
                <input
                  id="login-clave"
                  type={mostrarClave ? 'text' : 'password'}
                  placeholder="••••••••"
                  autoComplete="current-password"
                  enterKeyHint="done"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                <button
                  type="button"
                  className="campo-entrada-accion"
                  aria-label={mostrarClave ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  aria-pressed={mostrarClave}
                  onClick={() => setMostrarClave((v) => !v)}
                >
                  <Icono nombre={mostrarClave ? 'ojoCerrado' : 'ojo'} tamano={20} />
                </button>
              </div>
            </div>

            <button className="principal login-boton" type="submit" disabled={enviando || !email.trim() || !password}>
              {enviando && <span className="login-giro" aria-hidden="true" />}
              <span>{enviando ? 'Ingresando…' : 'Ingresar'}</span>
            </button>
          </form>

          <p className="login-ayuda">
            <Icono nombre="llave" tamano={18} />
            <span>¿Olvidaste tu contraseña? Pídele una temporal al administrador de tu empresa.</span>
          </p>

          <p className="login-pie">Esta app es solo para conductores. El panel se usa desde el navegador.</p>
        </div>
      </section>
    </main>
  );
}
