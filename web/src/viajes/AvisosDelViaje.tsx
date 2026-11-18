/**
 * HU-65 (CC-19, DC-62): cómo le llegan al pasajero los avisos del viaje (conductor asignado, llegada y cancelación).
 * Con Web Push aceptado en este navegador, como notificación; si no, por correo solo con la casilla de «Mi perfil».
 * El permiso se pide con un clic (los navegadores no permiten pedirlo solo).
 */

import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import { resultado } from '../api/resultado';
import { Boton } from '../diseno/Boton';
import e from '../diseno/diseno.module.css';
import { Tarjeta } from '../diseno/Tarjeta';
import { useApi } from '../sesion/SesionProvider';
import { claveComoBytes, pushDisponible } from './push';

type Estado = 'activo' | 'bloqueado' | 'disponible' | 'no_disponible' | 'revisando';

function estadoInicial(): Estado {
  if (!pushDisponible()) return 'no_disponible';
  if (Notification.permission === 'denied') return 'bloqueado';
  // Con permiso dado no basta: los avisos están activos solo si este navegador tiene la suscripción (DC-67).
  return Notification.permission === 'granted' ? 'revisando' : 'disponible';
}

export function AvisosDelViaje() {
  const api = useApi();
  const clave = useQuery({ queryKey: ['mi-cuenta', 'push'], queryFn: () => resultado(api.GET('/api/mi-cuenta/push/')), staleTime: Infinity });
  // La misma consulta que «Mi perfil»: la casilla de avisos por correo.
  const perfil = useQuery({ queryKey: ['mi-cuenta', 'perfil'], queryFn: () => resultado(api.GET('/api/mi-cuenta/')) });
  const aceptaCorreo = perfil.data?.acepta_avisos_correo ?? false;
  const [estado, setEstado] = useState<Estado>(estadoInicial);
  const [falla, setFalla] = useState<string | null>(null);
  const [activando, setActivando] = useState(false);
  const publica = clave.data?.clave_publica ?? null;

  useEffect(() => {
    if (estado !== 'revisando') return;
    let vigente = true;
    navigator.serviceWorker
      .getRegistration('/sw-push.js')
      .then((registro) => registro?.pushManager.getSubscription() ?? null)
      .catch(() => null)
      .then((suscripcion) => {
        if (vigente) setEstado(suscripcion ? 'activo' : 'disponible');
      });
    return () => {
      vigente = false;
    };
  }, [estado]);

  async function activar() {
    if (!publica) return;
    setFalla(null);
    setActivando(true);
    try {
      const permiso = await Notification.requestPermission();
      if (permiso !== 'granted') {
        setEstado(permiso === 'denied' ? 'bloqueado' : 'disponible');
        return;
      }
      await navigator.serviceWorker.register('/sw-push.js');
      // La primera vez el service worker aún se está instalando y sin uno activo la suscripción falla.
      const registro = await navigator.serviceWorker.ready;
      const suscripcion = await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: claveComoBytes(publica) });
      const datos = suscripcion.toJSON() as { endpoint: string; keys?: { p256dh: string; auth: string } };
      // Responde 201 sin cuerpo: basta con que haya salido bien.
      const { response } = await api.POST('/api/mi-cuenta/push/', { body: { endpoint: datos.endpoint, keys: datos.keys } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setEstado('activo');
    } catch {
      setFalla('No pudimos activar los avisos en este navegador. Intenta de nuevo.');
    } finally {
      setActivando(false);
    }
  }

  const correo = aceptaCorreo ? 'Si no, te avisamos por correo.' : 'También puedes recibirlos por correo desde';
  return (
    <Tarjeta como="section" aria-labelledby="titulo-avisos">
      <h2 id="titulo-avisos" className={e.conductorNombre}>
        Avisos de tu viaje
      </h2>
      {publica && estado === 'activo' && <p className={e.saludo}>Te avisaremos en este dispositivo cuando te asignen conductor, cuando llegue y si se cancela.</p>}
      {publica && estado === 'disponible' && (
        <>
          <p className={e.saludo}>Recibe un aviso en este dispositivo cuando te asignen conductor, cuando llegue y si se cancela.</p>
          <Boton variante="secundario" ancho cargando={activando} onClick={() => void activar()}>
            Activar avisos en este dispositivo
          </Boton>
        </>
      )}
      {publica && estado === 'bloqueado' && <p className={e.saludo}>Los avisos están bloqueados en este navegador. Puedes permitirlos en su configuración.</p>}
      {falla && (
        <p className={e.alerta} role="alert">
          {falla}
        </p>
      )}
      <p className={e.nota}>
        {aceptaCorreo ? (
          correo
        ) : (
          <>
            {correo} <Link to="/mi-perfil">Mi perfil</Link>.
          </>
        )}{' '}
        Esta página se actualiza sola.
      </p>
    </Tarjeta>
  );
}
