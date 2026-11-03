import { useEffect, useState } from 'react';
import type { EstadoEnvio } from '../gps/envio';
import type { EstadoRastreo } from '../gps/turno';
import { horaDeChile } from '../hora';
import { vehiculoParaTurno, type Perfil } from '../perfil';
import type { Asignacion } from '../conductor/canal';
import type { ViajeActivo } from '../navegacion';
import type { Usuario } from '../sesion/sesion';
import { ViajeEnCurso } from './ViajeEnCurso';

const ESTADOS = { DISPONIBLE: 'Disponible', NO_DISPONIBLE: 'No disponible', EN_VIAJE: 'En viaje' } as const;

interface Props {
  usuario: Usuario;
  perfil: Perfil;
  viaje: ViajeActivo | null;
  asignacion: Asignacion | null;
  verAsignacion: () => void;
  envio: EstadoEnvio;
  rastreo: EstadoRastreo;
  /** Cambia el turno; resuelve con el mensaje de error del backend, o null si se cambió. */
  cambiarTurno: (estado: 'DISPONIBLE' | 'NO_DISPONIBLE', vehiculo?: number) => Promise<string | null>;
  actualizar: () => void;
  abrirAjustes: () => void;
  cerrarSesion: () => void;
}

/** Inicio del conductor: empezar o terminar el turno con su vehículo (HU-13) y estado del GPS. */
export function Inicio({ usuario, perfil, viaje, asignacion, verAsignacion, envio, rastreo, cambiarTurno, actualizar, abrirAjustes, cerrarSesion }: Props) {
  const enTurno = perfil.estado !== 'NO_DISPONIBLE';
  const [elegido, setElegido] = useState<number | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [cambiando, setCambiando] = useState(false);
  const [confirmarSalida, setConfirmarSalida] = useState(false);
  const turno = vehiculoParaTurno(perfil, elegido);

  useEffect(() => {
    if (!confirmarSalida) return;
    const espera = setTimeout(() => setConfirmarSalida(false), 5000);
    return () => clearTimeout(espera);
  }, [confirmarSalida]);

  async function cambiar(estado: 'DISPONIBLE' | 'NO_DISPONIBLE') {
    setCambiando(true);
    setFalla(null);
    setFalla(await cambiarTurno(estado, estado === 'DISPONIBLE' ? turno.vehiculo : undefined));
    setCambiando(false);
  }

  return (
    <main>
      <h1>Hola, {usuario.nombre}</h1>
      <p className="secundario">{usuario.empresa.razon_social}</p>

      {asignacion && (
        <p className="aviso" role="status">
          Tienes un viaje asignado esperando tu respuesta.{' '}
          <button type="button" onClick={verAsignacion}>
            Ver viaje
          </button>
        </p>
      )}
      {viaje && <ViajeEnCurso viaje={viaje} />}

      <div className="tarjeta">
        <h2>Turno</h2>
        <dl>
          <dt>Estado</dt>
          <dd>{ESTADOS[perfil.estado]}</dd>
          <dt>Vehículo</dt>
          <dd>{perfil.vehiculo_activo?.patente ?? 'Sin declarar'}</dd>
        </dl>
        {falla && (
          <p className="error" role="alert">
            {falla}
          </p>
        )}

        {perfil.estado === 'NO_DISPONIBLE' &&
          (perfil.vehiculos.length === 0 ? (
            <p className="aviso">No tienes vehículos asociados. Habla con el administrador de tu empresa.</p>
          ) : (
            <>
              {perfil.vehiculos.length > 1 && (
                <fieldset className="vehiculos">
                  <legend>¿Qué vehículo usarás?</legend>
                  {perfil.vehiculos.map((vehiculo) => (
                    <label key={vehiculo.id} className="opcion">
                      <input
                        type="radio"
                        name="vehiculo"
                        checked={elegido === vehiculo.id}
                        onChange={() => setElegido(vehiculo.id)}
                      />
                      {vehiculo.patente} · {vehiculo.marca_modelo}
                    </label>
                  ))}
                </fieldset>
              )}
              <button className="principal" type="button" disabled={!turno.listo || cambiando} onClick={() => void cambiar('DISPONIBLE')}>
                {cambiando ? 'Empezando…' : 'Empezar turno (Disponible)'}
              </button>
            </>
          ))}
        {perfil.estado === 'DISPONIBLE' && (
          <button className="principal secundaria" type="button" disabled={cambiando} onClick={() => void cambiar('NO_DISPONIBLE')}>
            {cambiando ? 'Terminando…' : 'Terminar turno (No disponible)'}
          </button>
        )}
        {perfil.estado === 'EN_VIAJE' && <p className="secundario">Estás en un viaje: el turno sigue hasta terminarlo.</p>}
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
        {enTurno && (
          <details>
            <summary>Para que el GPS no se corte con la pantalla apagada</summary>
            <ol>
              <li>Ajustes de la app → Ahorro de batería → «Sin restricciones».</li>
              <li>Activa el inicio automático de la app.</li>
              <li>En apps recientes, deja la app con candado.</li>
              <li>Permiso de ubicación con «ubicación precisa».</li>
            </ol>
            <button type="button" onClick={abrirAjustes}>
              Abrir ajustes de la app
            </button>
          </details>
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
