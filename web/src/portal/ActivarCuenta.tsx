import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { ErrorApi, resultado } from '../api/resultado';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { LineaDeTiempo } from '../diseno/LineaDeTiempo';
import type { ClientePortal } from './api';
import { normalizarWhatsapp } from './telefono';

/** Cada cuánto se consulta si la cuenta ya se activó mientras la pantalla está abierta. */
export const CONSULTA_MS = 8_000;

interface Props {
  api: ClientePortal;
  slug: string;
  email: string;
  password: string;
  /** Número enmascarado al que se envió el mensaje. */
  telefono: string;
}

/**
 * HU-41: «Activa tu cuenta». Muestra el avance, espera la respuesta «CONFIRMAR CUENTA» consultando el estado,
 * reenvía el mensaje y corrige el número (con el correo y la contraseña del alta, con límite en el servidor).
 */
export function ActivarCuenta({ api, slug, email, password, telefono: inicial }: Props) {
  const [telefono, setTelefono] = useState(inicial);
  const [activa, setActiva] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [corrigiendo, setCorrigiendo] = useState(false);
  const [nuevo, setNuevo] = useState('');
  const [errorNumero, setErrorNumero] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    if (activa) return;
    const consultar = async () => {
      try {
        const estado = await resultado(api.POST('/api/portal/{slug}/cuenta/estado/', { params: { path: { slug } }, body: { email, password } }));
        if (estado.activa) setActiva(true);
      } catch {
        // Sin conexión o límite: se vuelve a intentar en la próxima vuelta.
      }
    };
    const intervalo = window.setInterval(() => void consultar(), CONSULTA_MS);
    return () => window.clearInterval(intervalo);
  }, [api, slug, email, password, activa]);

  async function reenviar(numero?: string) {
    setFalla(null);
    setAviso(null);
    setEnviando(true);
    try {
      const respuesta = await resultado(
        api.POST('/api/portal/{slug}/cuenta/reenviar/', { params: { path: { slug } }, body: { email, password, ...(numero && { telefono: numero }) } }),
      );
      setTelefono(respuesta.telefono);
      setAviso(numero ? `Corregimos tu número y te enviamos el mensaje al ${respuesta.telefono}.` : 'Te enviamos el mensaje de nuevo.');
      setCorrigiendo(false);
      return true;
    } catch (error) {
      const cuerpo = error instanceof ErrorApi ? ((error.cuerpo ?? {}) as Record<string, unknown>) : {};
      if (error instanceof ErrorApi && error.estado === 409) setActiva(true);
      else if (error instanceof ErrorApi && error.estado === 429) setFalla('Ya te reenviamos el mensaje varias veces. Espera unos minutos.');
      else if (Array.isArray(cuerpo.telefono)) setErrorNumero(String(cuerpo.telefono[0]));
      else setFalla('No se pudo reenviar el mensaje. Intenta de nuevo.');
      return false;
    } finally {
      setEnviando(false);
    }
  }

  function corregir(evento: FormEvent) {
    evento.preventDefault();
    const numero = normalizarWhatsapp(nuevo);
    if (!/^\+[1-9]\d{7,14}$/.test(numero)) {
      setErrorNumero('Revisa el número: 9 dígitos si es de Chile, o con + y el código si es de otro país.');
      return;
    }
    setErrorNumero(null);
    void reenviar(numero);
  }

  return (
    <div className={e.formulario}>
      <LineaDeTiempo
        etiqueta="Activación de tu cuenta"
        pasos={[
          { titulo: 'Cuenta creada', detalle: email, estado: 'hecho' },
          {
            titulo: 'Responde en WhatsApp',
            detalle: `Escribe CONFIRMAR CUENTA al mensaje que enviamos a ${telefono}`,
            estado: activa ? 'hecho' : 'actual',
          },
          { titulo: 'Listo para pedir viajes', estado: activa ? 'hecho' : 'pendiente' },
        ]}
      />
      <p className={e.esperando} data-activa={activa} role="status">
        {activa ? '¡Tu cuenta está activa!' : 'Esperando tu confirmación…'}
      </p>
      {activa ? (
        <Link to={`/solicitar/${slug}/ingresar`} className={claseBoton('principal', true)}>
          Ingresar
        </Link>
      ) : (
        <>
          {aviso && <p className={e.nota}>{aviso}</p>}
          {falla && (
            <p className={e.alerta} role="alert">
              {falla}
            </p>
          )}
          <Boton variante="secundario" ancho cargando={enviando && !corrigiendo} onClick={() => void reenviar()}>
            Reenviar mensaje de WhatsApp
          </Boton>
          {corrigiendo ? (
            <form className={e.formulario} onSubmit={corregir} noValidate aria-label="Corregir mi número">
              <Campo
                etiqueta="WhatsApp correcto"
                type="tel"
                autoComplete="tel-national"
                prefijo="+56"
                placeholder="9 1234 5678"
                ayuda="Número de Chile; si es de otro país, escríbelo con + y su código."
                value={nuevo}
                onChange={(evento) => setNuevo(evento.target.value)}
                error={errorNumero ?? undefined}
              />
              <Boton type="submit" ancho cargando={enviando}>
                Enviar al número nuevo
              </Boton>
            </form>
          ) : (
            <button type="button" className={`${e.destacadoAccion} ${e.centrado}`} onClick={() => setCorrigiendo(true)}>
              Corregir mi número
            </button>
          )}
        </>
      )}
    </div>
  );
}
