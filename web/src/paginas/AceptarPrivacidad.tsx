import { useEffect, useState, type FormEvent } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Boton } from '../diseno/Boton';
import { Casilla } from '../diseno/Campo';
import e from '../diseno/diseno.module.css';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaAcceso } from '../diseno/PantallaAcceso';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';

/**
 * DC-44 (Ley 21.719): el pasajero con una cuenta anterior al consentimiento único, o cuando cambia la versión del
 * aviso, lo acepta una vez antes de seguir. Queda registrado con la fecha y la versión.
 */
export function AceptarPrivacidad() {
  const { sesion, estado } = useSesion();
  const api = useApi();
  const navegar = useNavigate();
  const [acepta, setAcepta] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    document.title = 'Aviso de privacidad';
  }, []);

  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  if (!usuario.debe_aceptar_privacidad) return <Navigate to={inicioDeRol(usuario.rol)} replace />;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    if (!acepta) {
      setError('Para seguir debes aceptar el aviso de privacidad.');
      return;
    }
    setError(null);
    setFalla(null);
    setEnviando(true);
    try {
      await resultado(api.POST('/api/mi-cuenta/privacidad/', { body: { acepta: true } }));
      sesion.actualizarUsuario({ debe_aceptar_privacidad: false });
      navegar(inicioDeRol(usuario.rol), { replace: true });
    } catch {
      setFalla('No se pudo guardar tu respuesta. Intenta de nuevo.');
    } finally {
      setEnviando(false);
    }
  }

  const slug = usuario.empresa.slug;
  return (
    <MarcoPortal marca={usuario.empresa.razon_social} inicio="/aceptar-privacidad" barraMovil="oculta">
      <PantallaAcceso
        titulo="Antes de seguir"
        subtitulo="Actualizamos cómo te pedimos el consentimiento: lo aceptas una vez y queda en tu cuenta."
        movil="hero"
      >
        <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Aceptar el aviso de privacidad">
          {falla && <Aviso tipo="error">{falla}</Aviso>}
          <Casilla checked={acepta} onChange={(evento) => setAcepta(evento.target.checked)} error={error ?? undefined}>
            Acepto el <Link to={`/solicitar/${slug}/privacidad`}>aviso de privacidad</Link> de {usuario.empresa.razon_social} y recibir
            por WhatsApp los avisos de mis viajes.
          </Casilla>
          <Boton type="submit" ancho cargando={enviando}>
            {enviando ? 'Guardando…' : 'Aceptar y continuar'}
          </Boton>
          <button
            type="button"
            className={`${e.enlace} ${e.centrado}`}
            style={{ border: 0, background: 'none', cursor: 'pointer' }}
            onClick={() => void sesion.logout().then(() => navegar(`/solicitar/${slug}/ingresar`, { replace: true }))}
          >
            Cerrar sesión
          </button>
        </form>
      </PantallaAcceso>
    </MarcoPortal>
  );
}
