import { useState, type FormEvent } from 'react';
import { ErrorApi, SinRed, type SesionApp } from '../sesion/sesion';

const MINIMO = 10;

/** Cambio obligatorio de la contraseña temporal (DC-14). Hasta hacerlo, el backend no permite nada más. */
export function CambiarPassword({ sesion, nombre }: { sesion: SesionApp; nombre: string }) {
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);

  async function cambiar(evento: FormEvent) {
    evento.preventDefault();
    const locales: Record<string, string> = {};
    if (nueva.length < MINIMO) locales.password_nueva = `Usa al menos ${MINIMO} caracteres.`;
    else if (nueva === actual) locales.password_nueva = 'Debe ser distinta de la temporal.';
    if (repetida !== nueva) locales.repetida = 'No coincide con la nueva contraseña.';
    setErrores(locales);
    if (Object.keys(locales).length) return;
    setEnviando(true);
    try {
      await sesion.cambiarPassword(actual, nueva);
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400 && error.cuerpo) {
        setErrores(
          Object.fromEntries(Object.entries(error.cuerpo).map(([campo, valor]) => [campo, ([] as unknown[]).concat(valor).join(' ')])),
        );
      } else {
        setErrores({ general: error instanceof SinRed ? 'No se pudo conectar con el servidor.' : 'No se pudo cambiar la contraseña.' });
      }
      setEnviando(false);
    }
  }

  const campo = (clave: string) =>
    errores[clave] ? { 'aria-invalid': true as const, 'aria-describedby': `error-${clave}` } : {};

  return (
    <main>
      <h1>Crea tu contraseña</h1>
      <p>Hola, {nombre}. Ingresaste con una contraseña temporal: elige una propia para continuar.</p>
      {errores.general && (
        <p className="error" role="alert">
          {errores.general}
        </p>
      )}
      <form onSubmit={cambiar} noValidate>
        <label>
          Contraseña temporal
          <input type="password" autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} {...campo('password_actual')} />
          {errores.password_actual && <span id="error-password_actual" className="campo-error">{errores.password_actual}</span>}
        </label>
        <label>
          Nueva contraseña
          <input type="password" autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} {...campo('password_nueva')} />
          {errores.password_nueva ? (
            <span id="error-password_nueva" className="campo-error">{errores.password_nueva}</span>
          ) : (
            <span className="secundario">Al menos {MINIMO} caracteres; evita solo números o palabras comunes.</span>
          )}
        </label>
        <label>
          Repite la nueva contraseña
          <input type="password" autoComplete="new-password" value={repetida} onChange={(e) => setRepetida(e.target.value)} {...campo('repetida')} />
          {errores.repetida && <span id="error-repetida" className="campo-error">{errores.repetida}</span>}
        </label>
        <button className="principal" type="submit" disabled={enviando}>
          {enviando ? 'Guardando…' : 'Guardar y continuar'}
        </button>
      </form>
      <div className="acciones">
        <button type="button" onClick={() => void sesion.logout()}>
          Cerrar sesión
        </button>
      </div>
    </main>
  );
}
