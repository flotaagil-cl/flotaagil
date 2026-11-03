import { useEffect, useState } from 'react';
import type { EstadoEnvio } from '../gps/envio';
import type { EstadoRastreo } from '../gps/turno';
import { horaDeChile } from '../hora';
import type { Usuario } from '../sesion/sesion';
import type { Perfil } from '../perfil';

const ESTADOS = { DISPONIBLE: 'Disponible', NO_DISPONIBLE: 'No disponible', EN_VIAJE: 'En viaje' } as const;

interface Props {
  usuario: Usuario;
  perfil: Perfil;
  envio: EstadoEnvio;
  rastreo: EstadoRastreo;
  actualizar: () => void;
  abrirAjustes: () => void;
  cerrarSesion: () => void;
}

/** Inicio del conductor: su estado, el vehículo declarado y si se está registrando la ubicación. */
export function Inicio({ usuario, perfil, envio, rastreo, actualizar, abrirAjustes, cerrarSesion }: Props) {
  const enTurno = perfil.estado !== 'NO_DISPONIBLE';
  const [confirmarSalida, setConfirmarSalida] = useState(false);

  useEffect(() => {
    if (!confirmarSalida) return;
    const espera = setTimeout(() => setConfirmarSalida(false), 5000);
    return () => clearTimeout(espera);
  }, [confirmarSalida]);

  return (
    <main>
      <h1>Hola, {usuario.nombre}</h1>
      <p className="secundario">{usuario.empresa.razon_social}</p>

      <div className="tarjeta">
        <dl>
          <dt>Estado</dt>
          <dd>{ESTADOS[perfil.estado]}</dd>
          <dt>Vehículo</dt>
          <dd>{perfil.vehiculo_activo?.patente ?? 'Sin declarar'}</dd>
        </dl>
      </div>

      <div className="tarjeta" aria-live="polite">
        <h2>Ubicación</h2>
        {!enTurno ? (
          <p>No se registra: estás No disponible.</p>
        ) : rastreo.error === 'permiso' ? (
          <p className="error" role="alert">
            Falta el permiso de ubicación. Sin él no se puede registrar tu posición en turno.{' '}
            <button type="button" onClick={abrirAjustes}>
              Abrir ajustes
            </button>
          </p>
        ) : rastreo.error ? (
          <p className="error" role="alert">
            No se pudo iniciar el GPS.
          </p>
        ) : rastreo.activo ? (
          <>
            <p className="ok">Registrando tu ubicación ({perfil.estado === 'EN_VIAJE' ? 'cada 10 s' : 'cada 30 s'}).</p>
            {envio.ultimoEnvio && <p className="secundario">Último envío: {horaDeChile(envio.ultimoEnvio)}</p>}
            {envio.error === 'sin_conexion' && (
              <p className="aviso">Sin conexión: {envio.pendientes} posiciones esperan para enviarse.</p>
            )}
          </>
        ) : (
          <p>Iniciando el GPS…</p>
        )}
      </div>

      <div className="acciones">
        <button type="button" onClick={actualizar}>
          Actualizar
        </button>
        <button type="button" onClick={() => (confirmarSalida ? cerrarSesion() : setConfirmarSalida(true))}>
          {confirmarSalida ? (enTurno ? 'Confirmar: se detiene el GPS' : 'Confirmar cierre') : 'Cerrar sesión'}
        </button>
      </div>
    </main>
  );
}
