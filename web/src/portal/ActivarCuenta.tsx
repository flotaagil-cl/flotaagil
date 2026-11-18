import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { ErrorApi, resultado } from '../api/resultado';
import { Boton } from '../diseno/Boton';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { LineaDeTiempo } from '../diseno/LineaDeTiempo';
import type { ClientePortal } from './api';

/** Cada cuánto se consulta si la cuenta ya se activó mientras la pantalla está abierta. */
export const CONSULTA_MS = 8_000;

interface Props {
  api: ClientePortal;
  slug: string;
  email: string;
  password: string;
  /** Correo enmascarado al que se envió el enlace. */
  correo: string;
}

/**
 * HU-41 y HU-64 (DC-61): «Activa tu cuenta». Muestra el avance, espera a que se abra el enlace del correo (vale 24 h)
 * consultando el estado y permite reenviarlo (con el correo y la contraseña del alta, con límite en el servidor).
 */
export function ActivarCuenta({ api, slug, email, password, correo }: Props) {
  const [activa, setActiva] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
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

  async function reenviar() {
    setFalla(null);
    setAviso(null);
    setEnviando(true);
    try {
      const respuesta = await resultado(api.POST('/api/portal/{slug}/cuenta/reenviar/', { params: { path: { slug } }, body: { email, password } }));
      setAviso(`Te enviamos un enlace nuevo a ${respuesta.correo}.`);
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 409) setActiva(true);
      else if (error instanceof ErrorApi && error.estado === 429) setFalla('Ya te reenviamos el correo varias veces. Espera unos minutos.');
      else setFalla('No se pudo reenviar el correo. Intenta de nuevo.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className={e.formulario}>
      <LineaDeTiempo
        etiqueta="Activación de tu cuenta"
        pasos={[
          { titulo: 'Cuenta creada', detalle: email, estado: 'hecho' },
          {
            titulo: 'Abre el enlace del correo',
            detalle: `Te lo enviamos a ${correo}. Vale 24 horas; revisa también la carpeta de spam.`,
            estado: activa ? 'hecho' : 'actual',
          },
          { titulo: 'Listo para pedir viajes', estado: activa ? 'hecho' : 'pendiente' },
        ]}
      />
      <p className={e.esperando} data-activa={activa} role="status">
        {activa ? '¡Tu cuenta está activa!' : 'Esperando que abras el enlace…'}
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
          <Boton variante="secundario" ancho cargando={enviando} onClick={() => void reenviar()}>
            Reenviar el correo
          </Boton>
        </>
      )}
    </div>
  );
}
