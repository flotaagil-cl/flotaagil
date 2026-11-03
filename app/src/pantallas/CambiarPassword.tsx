import { cloneElement, useState, type FormEvent, type ReactElement } from 'react';
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
        <Campo id="password_actual" etiqueta="Contraseña temporal" error={errores.password_actual}>
          <input type="password" autoComplete="current-password" value={actual} onChange={(e) => setActual(e.target.value)} />
        </Campo>
        <Campo
          id="password_nueva"
          etiqueta="Nueva contraseña"
          error={errores.password_nueva}
          ayuda={`Al menos ${MINIMO} caracteres; evita solo números o palabras comunes.`}
        >
          <input type="password" autoComplete="new-password" value={nueva} onChange={(e) => setNueva(e.target.value)} />
        </Campo>
        <Campo id="repetida" etiqueta="Repite la nueva contraseña" error={errores.repetida}>
          <input type="password" autoComplete="new-password" value={repetida} onChange={(e) => setRepetida(e.target.value)} />
        </Campo>
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

/** Etiqueta y control; la ayuda y el error van fuera de la etiqueta, enlazados con aria-describedby. */
function Campo({ id, etiqueta, error, ayuda, children }: { id: string; etiqueta: string; error?: string; ayuda?: string; children: ReactElement<Record<string, unknown>> }) {
  const descripcion = error ? `${id}-error` : ayuda ? `${id}-ayuda` : undefined;
  return (
    <div className="campo">
      <label htmlFor={id}>{etiqueta}</label>
      {cloneElement(children, { id, 'aria-invalid': error ? true : undefined, 'aria-describedby': descripcion })}
      {error ? (
        <span id={`${id}-error`} className="campo-error">
          {error}
        </span>
      ) : (
        ayuda && (
          <span id={`${id}-ayuda`} className="secundario">
            {ayuda}
          </span>
        )
      )}
    </div>
  );
}
