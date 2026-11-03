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
import { modoDeRastreo, type Perfil } from './perfil';
import { api, cola, rastreador, sesion } from './servicios';
import { SinRed, type EstadoSesion } from './sesion/sesion';

export default function App() {
  const [estado, setEstado] = useState<EstadoSesion>(sesion.estado);
  const [perfil, setPerfil] = useState<Perfil | null>(null);
  const [fallaPerfil, setFallaPerfil] = useState<string | null>(null);
  const [envio, setEnvio] = useState<EstadoEnvio>(cola.estado);
  const [rastreo, setRastreo] = useState<EstadoRastreo>(rastreador.estado);

  useEffect(() => sesion.suscribir(setEstado), []);
  useEffect(() => cola.suscribir(setEnvio), []);
  useEffect(() => rastreador.suscribir(setRastreo), []);
  useEffect(() => {
    void sesion.iniciar();
  }, []);

  const activa = estado.fase === 'activa';

  const cargarPerfil = useCallback(async () => {
    try {
      setPerfil(await api.pedir<Perfil>('GET', '/api/app/perfil/'));
      setFallaPerfil(null);
    } catch (error) {
      setFallaPerfil(error instanceof SinRed ? 'Sin conexión con el servidor.' : 'No se pudo cargar tu información.');
    }
  }, []);

  // Perfil al entrar y al volver a la app (otro dispositivo o el panel pudo cambiar el estado).
  useEffect(() => {
    if (!activa) return;
    void cargarPerfil();
    const escucha = AppNativa.addListener('resume', () => void cargarPerfil());
    return () => {
      void escucha.then((e) => e.remove());
    };
  }, [activa, cargarPerfil]);

  // Si el backend dice que ya no está en turno o no hay consentimiento, se recarga el perfil (y se detiene).
  useEffect(() => {
    if (envio.detenido) void cargarPerfil();
  }, [envio.detenido, cargarPerfil]);

  const modo = activa ? modoDeRastreo(perfil) : null;
  useEffect(() => {
    if (modo) void rastreador.iniciar(modo);
    else void rastreador.detener();
  }, [modo]);

  async function cerrarSesion() {
    await rastreador.detener();
    cola.vaciarSinEnviar();
    setPerfil(null);
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
  if (!perfil.consentimiento_gps_en) {
    return <Consentimiento alAceptar={async () => setPerfil(await api.pedir<Perfil>('POST', '/api/app/consentimiento/'))} />;
  }
  return (
    <Inicio
      usuario={estado.usuario}
      perfil={perfil}
      envio={envio}
      rastreo={rastreo}
      actualizar={() => void cargarPerfil()}
      abrirAjustes={() => void abrirAjustes()}
      cerrarSesion={() => void cerrarSesion()}
    />
  );
}
