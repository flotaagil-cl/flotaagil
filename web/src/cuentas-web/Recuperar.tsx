import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { Link, useParams, useSearchParams } from 'react-router';
import { ErrorApi, resultado } from '../api/resultado';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaAcceso } from '../diseno/PantallaAcceso';
import { MINIMO_PASSWORD, reglasPassword } from '../diseno/password';
import { ReglasPassword } from '../diseno/ReglasPassword';
import { Destacado } from '../diseno/Tarjeta';
import { useEntorno } from '../entornoContexto';
import { crearClientePortal, type ClientePortal } from '../portal/api';

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

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

/**
 * HU-41: marco de las pantallas públicas de la contraseña. Con `?empresa=<slug>` (el ingreso del portal y el correo
 * lo agregan) muestra la marca de la empresa y el ingreso vuelve a su portal.
 */
function useMarca(api: ClientePortal) {
  const [parametros] = useSearchParams();
  const slug = SLUG.test(parametros.get('empresa') ?? '') ? parametros.get('empresa')! : null;
  // Ruta pública sin proveedor de consultas: la empresa se carga una vez con un efecto.
  const [razonSocial, setRazonSocial] = useState<string | null>(null);
  useEffect(() => {
    if (slug === null) return;
    let vigente = true;
    resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug } } }))
      .then((empresa) => vigente && setRazonSocial(empresa.razon_social))
      .catch(() => undefined);
    return () => {
      vigente = false;
    };
  }, [api, slug]);
  const conEmpresa = slug !== null && razonSocial !== null;
  return {
    marca: conEmpresa ? razonSocial : 'FlotaÁgil',
    ingresar: conEmpresa ? `/solicitar/${slug}/ingresar` : '/login',
    sufijo: conEmpresa ? `?empresa=${slug}` : '',
  };
}

function Marco({ marca, ingresar, children }: { marca: string; ingresar: string; children: ReactNode }) {
  return (
    <MarcoPortal marca={marca} inicio={ingresar} barraMovil="oculta">
      {children}
    </MarcoPortal>
  );
}

/** HU-41: pide el enlace (vence a los 30 min). Responde lo mismo exista o no el correo. */
export function Recuperar() {
  const api = useClientePublico();
  const { marca, ingresar } = useMarca(api);
  const [email, setEmail] = useState('');
  const [enviado, setEnviado] = useState(false);
  const [reenviado, setReenviado] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    document.title = `Recupera tu contraseña · ${marca}`;
  }, [marca]);

  async function pedir() {
    setFalla(null);
    setEnviando(true);
    try {
      await sinCuerpo(api.POST('/api/auth/recuperar/', { body: { email: email.trim() } }));
      return true;
    } catch (problema) {
      setFalla(problema instanceof ErrorApi && problema.estado === 429 ? 'Demasiados intentos. Espera un momento.' : 'No se pudo enviar. Intenta de nuevo.');
      return false;
    } finally {
      setEnviando(false);
    }
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim())) {
      setError('Ingresa un correo válido.');
      return;
    }
    setError(null);
    if (await pedir()) setEnviado(true);
  }

  if (enviado) {
    return (
      <Marco marca={marca} ingresar={ingresar}>
        <PantallaAcceso titulo="Revisa tu correo" subtitulo="Te enviamos un enlace para crear una contraseña nueva." movil="hero" volver={{ a: ingresar, texto: 'Volver a ingresar' }}>
          <Destacado titulo={email.trim()} icono="mensaje">
            Si es el correo de tu cuenta, el enlace llega en unos minutos. Vence en 30 minutos y sirve una sola vez.
          </Destacado>
          {falla && (
            <p className={e.alerta} role="alert">
              {falla}
            </p>
          )}
          {reenviado && <p role="status" className={e.nota}>Te lo enviamos de nuevo.</p>}
          <Boton
            variante="secundario"
            ancho
            cargando={enviando}
            onClick={() => void pedir().then((ok) => setReenviado(ok))}
          >
            Reenviar el enlace
          </Boton>
          <p className={e.nota}>¿No lo ves? Revisa la carpeta de spam. Puedes pedirlo hasta 3 veces cada 15 minutos.</p>
          <Link to={ingresar} className={`${e.enlace} ${e.centrado}`}>
            Volver a ingresar
          </Link>
        </PantallaAcceso>
      </Marco>
    );
  }

  return (
    <Marco marca={marca} ingresar={ingresar}>
      <PantallaAcceso
        titulo="Recupera tu contraseña"
        subtitulo="Escribe el correo de tu cuenta y te enviaremos un enlace para crear una nueva."
        movil="hero"
        volver={{ a: ingresar, texto: 'Volver a ingresar' }}
      >
        <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Recupera tu contraseña">
          {falla && (
            <p className={e.alerta} role="alert">
              {falla}
            </p>
          )}
          <Campo
            etiqueta="Correo"
            type="email"
            autoComplete="email"
            inputMode="email"
            placeholder="nombre@correo.cl"
            value={email}
            onChange={(evento) => setEmail(evento.target.value)}
            error={error ?? undefined}
          />
          <Boton type="submit" ancho cargando={enviando}>
            {enviando ? 'Enviando…' : 'Enviar enlace'}
          </Boton>
          <Link to={ingresar} className={`${e.enlace} ${e.centrado}`}>
            Volver a ingresar
          </Link>
        </form>
      </PantallaAcceso>
    </Marco>
  );
}

/** HU-41: crea la contraseña nueva con el enlace del correo, con las reglas a la vista. */
export function ElegirPassword() {
  const { uid = '', token = '' } = useParams();
  const api = useClientePublico();
  const { marca, ingresar, sufijo } = useMarca(api);
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [listo, setListo] = useState(false);
  const [errores, setErrores] = useState<{ nueva?: string; repetida?: string; token?: string; general?: string }>({});
  const [guardando, setGuardando] = useState(false);
  const reglas = reglasPassword(nueva, repetida);

  useEffect(() => {
    document.title = `Crea una nueva contraseña · ${marca}`;
  }, [marca]);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados: typeof errores = {};
    if (nueva.length < MINIMO_PASSWORD) encontrados.nueva = `Mínimo ${MINIMO_PASSWORD} caracteres.`;
    else if (/^\d+$/.test(nueva)) encontrados.nueva = 'No puede tener solo números.';
    if (repetida !== nueva) encontrados.repetida = 'Las contraseñas no coinciden.';
    setErrores(encontrados);
    if (Object.keys(encontrados).length) return;
    setGuardando(true);
    try {
      await sinCuerpo(api.POST('/api/auth/recuperar/confirmar/', { body: { uid, token, password: nueva } }));
      setListo(true);
    } catch (falla) {
      const cuerpo = falla instanceof ErrorApi ? ((falla.cuerpo ?? {}) as Record<string, string[] | undefined>) : {};
      if (cuerpo.token?.[0]) setErrores({ token: cuerpo.token[0] });
      else if (cuerpo.password?.[0]) setErrores({ nueva: cuerpo.password[0] });
      else setErrores({ general: 'No se pudo cambiar la contraseña. Intenta de nuevo.' });
    } finally {
      setGuardando(false);
    }
  }

  if (listo) {
    return (
      <Marco marca={marca} ingresar={ingresar}>
        <PantallaAcceso titulo="Tu contraseña quedó lista" subtitulo="Ya puedes ingresar con tu contraseña nueva." movil="hero">
          <Link to={ingresar} className={claseBoton('principal', true)}>
            Ingresar
          </Link>
        </PantallaAcceso>
      </Marco>
    );
  }

  return (
    <Marco marca={marca} ingresar={ingresar}>
      <PantallaAcceso titulo="Crea una nueva contraseña" subtitulo="Elige una que no hayas usado antes." movil="hero">
        <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Crea una nueva contraseña">
          {(errores.token || errores.general) && (
            <p className={e.alerta} role="alert">
              {errores.token ?? errores.general}{' '}
              {errores.token && (
                <Link to={`/recuperar${sufijo}`}>Pedir un enlace nuevo</Link>
              )}
            </p>
          )}
          <Campo
            etiqueta="Nueva contraseña"
            type="password"
            autoComplete="new-password"
            value={nueva}
            onChange={(evento) => setNueva(evento.target.value)}
            error={errores.nueva}
            aria-describedby="reglas-password"
          />
          <Campo
            etiqueta="Repite la contraseña"
            type="password"
            autoComplete="new-password"
            value={repetida}
            onChange={(evento) => setRepetida(evento.target.value)}
            error={errores.repetida}
          />
          <ReglasPassword reglas={reglas} id="reglas-password" />
          <Boton type="submit" ancho cargando={guardando}>
            {guardando ? 'Guardando…' : 'Guardar contraseña'}
          </Boton>
        </form>
      </PantallaAcceso>
    </Marco>
  );
}
