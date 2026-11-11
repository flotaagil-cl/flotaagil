import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { ErrorApi, resultado } from '../../api/resultado';
import { Boton } from '../../diseno/Boton';
import { Campo } from '../../diseno/Campo';
import e from '../../diseno/diseno.module.css';
import { PantallaAcceso } from '../../diseno/PantallaAcceso';
import { ActivarCuenta } from '../ActivarCuenta';
import { useContextoPortal } from '../contexto';

/**
 * HU-41: volver a «Activa tu cuenta» después de cerrar la pantalla del alta. Pide el correo y la contraseña de la
 * cuenta para reenviar el mensaje o corregir el número.
 */
export function Activar() {
  const { api, slug } = useContextoPortal();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [telefono, setTelefono] = useState<string | null>(null);
  const [activa, setActiva] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const ingresar = `/solicitar/${slug}/ingresar`;

  async function buscar(evento: FormEvent) {
    evento.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const estado = await resultado(api.POST('/api/portal/{slug}/cuenta/estado/', { params: { path: { slug } }, body: { email: email.trim(), password } }));
      setActiva(estado.activa);
      setTelefono(estado.telefono);
    } catch (falla) {
      setError(
        falla instanceof ErrorApi && falla.estado === 400
          ? 'No encontramos una cuenta por activar con ese correo y contraseña.'
          : falla instanceof ErrorApi && falla.estado === 429
            ? 'Demasiados intentos. Espera un momento.'
            : 'No se pudo consultar. Intenta de nuevo.',
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <PantallaAcceso
      titulo="Activa tu cuenta"
      subtitulo="Un último paso: confirma que el WhatsApp es tuyo."
      movil="hero"
      volver={{ a: ingresar, texto: 'Volver a ingresar' }}
    >
      {telefono !== null && activa && (
        <>
          <p className={e.esperando} data-activa="true" role="status">
            Tu cuenta ya está activa.
          </p>
          <Link to={ingresar} className={`${e.enlace} ${e.centrado}`}>
            Ingresar
          </Link>
        </>
      )}
      {telefono !== null && !activa && <ActivarCuenta api={api} slug={slug} email={email.trim()} password={password} telefono={telefono} />}
      {telefono === null && (
        <form className={e.formulario} onSubmit={(evento) => void buscar(evento)} noValidate aria-label="Buscar mi cuenta">
          {error && (
            <p className={e.alerta} role="alert">
              {error}
            </p>
          )}
          <Campo etiqueta="Correo" type="email" autoComplete="email" inputMode="email" value={email} onChange={(evento) => setEmail(evento.target.value)} />
          <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" value={password} onChange={(evento) => setPassword(evento.target.value)} />
          <Boton type="submit" ancho cargando={enviando}>
            Continuar
          </Boton>
        </form>
      )}
    </PantallaAcceso>
  );
}
