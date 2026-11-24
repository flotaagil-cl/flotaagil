import { cloneElement, useState, type FormEvent, type ReactElement } from 'react';
import { Icono } from '../componentes/Icono';
import { useAtras } from '../atras';
import { ErrorApi, SinRed, type SesionApp } from '../sesion/sesion';

const MINIMO = 10;

/** Cambio obligatorio de la contraseña temporal (DC-14). Hasta hacerlo, el backend no permite nada más. */
export function CambiarPassword({ sesion, nombre }: { sesion: SesionApp; nombre: string }) {
  return (
    <main>
      <h1>Crea tu contraseña</h1>
      <p>Hola, {nombre}. Ingresaste con una contraseña temporal: elige una propia para continuar.</p>
      <FormularioPassword sesion={sesion} etiquetaActual="Contraseña temporal" textoBoton="Guardar y continuar" distinta="Debe ser distinta de la temporal." />
      <div className="acciones">
        <button type="button" onClick={() => void sesion.logout()}>
          Cerrar sesión
        </button>
      </div>
    </main>
  );
}

/**
 * HU-74 (DC-78): el conductor cambia su contraseña cuando quiera, desde el menú de la app. Pide la actual; al
 * guardar, el backend cierra sus otras sesiones y deja esta con tokens nuevos. Queda en auditoría.
 */
export function CambiarMiPassword({ sesion, volver }: { sesion: SesionApp; volver: () => void }) {
  const [listo, setListo] = useState(false);
  useAtras(volver);
  return (
    <main className="app-pantalla">
      <header className="app-barra">
        <button type="button" className="barra-atras" aria-label="Volver" onClick={volver}>
          <Icono nombre="atras" tamano={22} />
        </button>
        <div className="barra-titulos">
          <h1>Cambiar contraseña</h1>
          <p className="barra-subtitulo">Tu acceso a la app</p>
        </div>
      </header>
      <div className="app-cuerpo">
        {listo ? (
          <div className="tarjeta">
            <p role="status">Listo: tu contraseña cambió. Cerramos tus sesiones en otros teléfonos.</p>
            <button type="button" className="principal" onClick={volver}>
              Volver al inicio
            </button>
          </div>
        ) : (
          <div className="tarjeta">
            <FormularioPassword
              sesion={sesion}
              etiquetaActual="Contraseña actual"
              textoBoton="Cambiar contraseña"
              distinta="Debe ser distinta de la actual."
              alCambiar={() => setListo(true)}
            />
          </div>
        )}
      </div>
    </main>
  );
}

function FormularioPassword({
  sesion,
  etiquetaActual,
  textoBoton,
  distinta,
  alCambiar,
}: {
  sesion: SesionApp;
  etiquetaActual: string;
  textoBoton: string;
  distinta: string;
  alCambiar?: () => void;
}) {
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);

  async function cambiar(evento: FormEvent) {
    evento.preventDefault();
    const locales: Record<string, string> = {};
    if (nueva.length < MINIMO) locales.password_nueva = `Usa al menos ${MINIMO} caracteres.`;
    else if (nueva === actual) locales.password_nueva = distinta;
    if (repetida !== nueva) locales.repetida = 'No coincide con la nueva contraseña.';
    setErrores(locales);
    if (Object.keys(locales).length) return;
    setEnviando(true);
    try {
      await sesion.cambiarPassword(actual, nueva);
      alCambiar?.();
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
    <>
      {errores.general && (
        <p className="error" role="alert">
          {errores.general}
        </p>
      )}
      <form onSubmit={cambiar} noValidate>
        <Campo id="password_actual" etiqueta={etiquetaActual} error={errores.password_actual}>
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
          {enviando ? 'Guardando…' : textoBoton}
        </button>
      </form>
    </>
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
