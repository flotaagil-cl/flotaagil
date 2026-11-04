/**
 * Flujo de la app: login (canal app) → cambio de la contraseña temporal si corresponde (DC-14) → consentimiento
 * de ubicación (RN-18) → inicio. El GPS corre solo en turno y con consentimiento; se detiene al cerrar sesión.
 */

import { App as AppNativa } from '@capacitor/app';
import { useCallback, useEffect, useState } from 'react';
import { abrirAjustes } from './gps/rastreo';
import type { EstadoEnvio } from './gps/envio';
import type { EstadoRastreo } from './gps/turno';
import { CambiarPassword } from './pantallas/CambiarPassword';
import { Consentimiento } from './pantallas/Consentimiento';
import { Inicio } from './pantallas/Inicio';
import { Login } from './pantallas/Login';
import { MiTurno, type ResumenDelTurno } from './pantallas/MiTurno';
import type { ViajeActivo } from './navegacion';
import { modoDeRastreo, type Perfil } from './perfil';
import { alertar, pedirPermisoDeNotificaciones } from './conductor/alerta';
import type { Accion } from './conductor/ejecucion';
import { Recarga } from './conductor/recarga';
import type { Pago } from './pantallas/AvanceViaje';
import type { EstadoCanal } from './conductor/canal';
import { Responder } from './pantallas/Responder';
import { ViajeAsignado } from './pantallas/ViajeAsignado';
import { api, canal, cola, rastreador, sesion } from './servicios';
import { ErrorApi, SinRed, type EstadoSesion } from './sesion/sesion';

export default function App() {
  const [estado, setEstado] = useState<EstadoSesion>(sesion.estado);
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [viaje, setViaje] = useState<ViajeActivo | null>(null);
  const [fallaPerfil, setFallaPerfil] = useState<string | null>(null);
  const [envio, setEnvio] = useState<EstadoEnvio>(cola.estado);
  const [rastreo, setRastreo] = useState<EstadoRastreo>(rastreador.estado);
  const [enVivo, setEnVivo] = useState<EstadoCanal>(canal.estado);
  const [avisoOculto, setAvisoOculto] = useState<number | null>(null);
  const [enMiTurno, setEnMiTurno] = useState(false);
  const cargarMiTurno = useCallback(() => api.pedir<ResumenDelTurno>('GET', '/api/app/mi-turno/'), []);

  useEffect(() => sesion.suscribir(setEstado), []);
  useEffect(() => cola.suscribir(setEnvio), []);
  useEffect(() => rastreador.suscribir(setRastreo), []);
  useEffect(() => canal.suscribir(setEnVivo), []);
  // HU-14: alerta sonora y vibración; notificación del sistema si la app no está a la vista.
  useEffect(() => canal.alRecibirAsignacion((asignacion) => void alertar(asignacion, document.hidden)), []);
  useEffect(() => {
    void sesion.iniciar();
  }, []);

  const activa = estado.fase === 'activa';

  // Perfil y viaje activo: gana la última lectura y, si falla o no responde, se reintenta sola.
  const [recarga] = useState(
    () =>
      new Recarga(
        () =>
          Promise.all([
            api.pedir<Perfil>('GET', '/api/app/perfil/'),
            api.pedir<{ viaje: ViajeActivo | null }>('GET', '/api/app/viaje-activo/'),
          ]),
        ([nuevo, activo]) => {
          setPerfil(nuevo);
          setViaje(activo.viaje);
          setFallaPerfil(null);
        },
        (error) => {
          setFallaPerfil(error instanceof SinRed ? 'Sin conexión con el servidor.' : 'No se pudo cargar tu información.');
        },
      ),
  );
  const cargarPerfil = useCallback(() => recarga.recargar(), [recarga]);

  // Perfil al entrar y al volver a la app (otro dispositivo o el panel pudo cambiar el estado).
  useEffect(() => {
    if (!activa) return;
    recarga.iniciar();
    void cargarPerfil();
    const escucha = AppNativa.addListener('resume', () => void cargarPerfil());
    return () => {
      recarga.detener();
      void escucha.then((e) => e.remove());
    };
  }, [activa, cargarPerfil, recarga]);

  // Si el backend dice que ya no está en turno o no hay consentimiento, se recarga el perfil (y se detiene).
  useEffect(() => {
    if (envio.detenido) void cargarPerfil();
  }, [envio.detenido, cargarPerfil]);

  // El canal en vivo corre mientras haya sesión activa; las notificaciones se piden al entrar.
  useEffect(() => {
    if (!activa) return;
    void pedirPermisoDeNotificaciones();
    canal.iniciar();
    return () => canal.detener();
  }, [activa]);

  // Al asignarse un viaje se recarga el perfil (el viaje en curso aparece al aceptarlo, HU-15).
  const asignacionId = enVivo.asignacion?.asignacion ?? null;
  useEffect(() => {
    if (asignacionId !== null) void cargarPerfil();
  }, [asignacionId, cargarPerfil]);

  // HU-16: EN_ZONA automático o cancelación desde el panel. Al reconectarse también, por si se perdió el aviso.
  useEffect(() => canal.alCambiarViaje(() => void cargarPerfil()), [cargarPerfil]);
  useEffect(() => {
    if (enVivo.conectado) void cargarPerfil();
  }, [enVivo.conectado, cargarPerfil]);

  const modo = activa ? modoDeRastreo(perfil) : null;
  useEffect(() => {
    if (modo) void rastreador.iniciar(modo);
    else void rastreador.detener();
  }, [modo]);

  /** HU-13: Disponible (con el vehículo del turno) o No disponible. Devuelve el mensaje de error o null. */
  async function cambiarTurno(estado: 'DISPONIBLE' | 'NO_DISPONIBLE', vehiculo?: number): Promise<string | null> {
    try {
      setPerfil(await api.pedir<Perfil>('POST', '/api/app/turno/', { estado, ...(vehiculo && { vehiculo }) }));
      return null;
    } catch (error) {
      if (error instanceof SinRed) return 'No se pudo conectar con el servidor. Intenta de nuevo.';
      if (error instanceof ErrorApi && error.estado === 409) {
        void cargarPerfil();
        return error.message;
      }
      return 'No se pudo cambiar el estado.';
    }
  }

  /** HU-15: aceptar o rechazar dentro de los 60 s. Devuelve el mensaje de error o null. */
  async function responderAsignacion(id: number, aceptar: boolean): Promise<string | null> {
    try {
      await api.pedir('POST', `/api/app/asignaciones/${id}/${aceptar ? 'aceptar' : 'rechazar'}/`);
      canal.olvidar(id);
      void cargarPerfil();
      return null;
    } catch (error) {
      // Sin respuesta no se sabe si llegó: se vuelve a leer para mostrar lo que hay en el servidor.
      void cargarPerfil();
      if (error instanceof SinRed) return 'No se pudo conectar con el servidor. Intenta de nuevo.';
      if (error instanceof ErrorApi && error.estado === 409) {
        canal.olvidar(id);
        return error.message;
      }
      return 'No se pudo registrar tu respuesta.';
    }
  }

  /** HU-16: paso siguiente del viaje en curso. Devuelve el mensaje de error o null. */
  async function avanzarViaje(accion: Accion | 'finalizar', pago?: Pago): Promise<string | null> {
    if (!viaje) return null;
    try {
      await api.pedir('POST', `/api/app/viajes/${viaje.id}/${accion}/`, pago);
      await cargarPerfil();
      return null;
    } catch (error) {
      // Sin respuesta no se sabe si llegó, y con 409 el viaje cambió por otro lado: se muestra lo que hay ahora.
      void cargarPerfil();
      if (error instanceof SinRed) return 'No se pudo conectar con el servidor. Intenta de nuevo.';
      if (error instanceof ErrorApi && error.estado === 409) return error.message;
      return 'No se pudo registrar el cambio.';
    }
  }

  async function cerrarSesion() {
    canal.detener();
    await rastreador.detener();
    cola.vaciarSinEnviar();
    setPerfil(null);
    setViaje(null);
    setEnMiTurno(false);
    await sesion.logout();
  }

  if (estado.fase === 'cargando') {
    return (
      <main>
        <p>Cargando…</p>
      </main>
    );
  }
  if (estado.fase === 'sin_sesion') return <Login sesion={sesion} motivo={estado.motivo} />;
  if (estado.fase === 'cambio_pendiente') return <CambiarPassword sesion={sesion} nombre={estado.usuario.nombre} />;
  if (!perfil) {
    return (
      <main>
        {fallaPerfil ? (
          <p className="error" role="alert">
            {fallaPerfil}{' '}
            <button type="button" onClick={() => void cargarPerfil()}>
              Reintentar
            </button>
          </p>
        ) : (
          <p>Cargando…</p>
        )}
      </main>
    );
  }
  if (enVivo.asignacion && avisoOculto !== enVivo.asignacion.asignacion) {
    const id = enVivo.asignacion.asignacion;
    return (
      <ViajeAsignado
        asignacion={enVivo.asignacion}
        acciones={
          <Responder
            asignacion={enVivo.asignacion}
            responder={(aceptar) => responderAsignacion(id, aceptar)}
            ocultar={() => {
              setAvisoOculto(id);
              canal.olvidar(id);
            }}
          />
        }
      />
    );
  }
  if (!perfil.consentimiento_gps_en) {
    return <Consentimiento alAceptar={async () => setPerfil(await api.pedir<Perfil>('POST', '/api/app/consentimiento/'))} />;
  }
  if (enMiTurno) return <MiTurno cargar={cargarMiTurno} volver={() => setEnMiTurno(false)} />;
  return (
    <Inicio
      usuario={estado.usuario}
      perfil={perfil}
      viaje={viaje}
      avanzar={avanzarViaje}
      asignacion={enVivo.asignacion}
      verAsignacion={() => setAvisoOculto(null)}
      envio={envio}
      rastreo={rastreo}
      cambiarTurno={cambiarTurno}
      actualizar={() => void cargarPerfil()}
      verMiTurno={() => setEnMiTurno(true)}
      abrirAjustes={() => void abrirAjustes()}
      cerrarSesion={() => void cerrarSesion()}
    />
  );
}
