import { useEffect, useState } from 'react';
import type { MensajeChat } from '../chat/canal';
import { DeslizarParaActualizar } from '../componentes/DeslizarParaActualizar';
import type { Asignacion } from '../conductor/canal';
import type { Accion } from '../conductor/ejecucion';
import type { EstadoEnvio } from '../gps/envio';
import type { EstadoRastreo } from '../gps/turno';
import { horaDeChile } from '../hora';
import type { ViajeActivo } from '../navegacion';
import { vehiculoParaTurno, type Perfil } from '../perfil';
import type { Usuario } from '../sesion/sesion';
import { AvanceViaje, type Pago } from './AvanceViaje';
import { Responder } from './Responder';
import { ViajeAsignado } from './ViajeAsignado';
import { ViajeEnCurso } from './ViajeEnCurso';

const ESTADOS = { DISPONIBLE: 'Disponible', NO_DISPONIBLE: 'No disponible', EN_VIAJE: 'En viaje' } as const;

interface Props {
  usuario: Usuario;
  perfil: Perfil;
  viaje: ViajeActivo | null;
  avanzar: (accion: Accion | 'finalizar', pago?: Pago) => Promise<string | null>;
  asignacion: Asignacion | null;
  responder: (id: number, aceptar: boolean) => Promise<string | null>;
  ocultarAsignacion: (id: number) => void;
  envio: EstadoEnvio;
  rastreo: EstadoRastreo;
  /** Cambia el turno; resuelve con el mensaje de error del backend, o null si se cambió. */
  cambiarTurno: (estado: 'DISPONIBLE' | 'NO_DISPONIBLE', vehiculo?: number) => Promise<string | null>;
  actualizar: () => Promise<unknown>;
  verMiTurno: () => void;
  /** CC-19: abre el chat; `noLeidos` se muestra en el botón. */
  verChat: () => void;
  noLeidos: number;
  /** HU-63: último mensaje ajeno recibido fuera del chat. */
  avisoChat?: MensajeChat | null;
  abrirAjustes: () => void;
  cerrarSesion: () => void;
}

/** Inicio del conductor: tarjeta prioritaria de viaje (HU-14/15/16/17), turno (HU-13) y estado del GPS. */
export function Inicio({
  usuario,
  perfil,
  viaje,
  avanzar,
  asignacion,
  responder,
  ocultarAsignacion,
  envio,
  rastreo,
  cambiarTurno,
  actualizar,
  verMiTurno,
  verChat,
  noLeidos,
  avisoChat,
  abrirAjustes,
  cerrarSesion,
}: Props) {
  const enTurno = perfil.estado !== 'NO_DISPONIBLE';
  const hayViaje = Boolean(viaje || asignacion);
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
    <DeslizarParaActualizar alActualizar={actualizar}>
      <main>
        <h1>Hola, {usuario.nombre}</h1>
        <p className="secundario">{usuario.empresa.razon_social}</p>

        {asignacion && (
          <ViajeAsignado
            asignacion={asignacion}
            acciones={
              <Responder
                asignacion={asignacion}
                responder={(aceptar) => responder(asignacion.asignacion, aceptar)}
                ocultar={() => ocultarAsignacion(asignacion.asignacion)}
              />
            }
          />
        )}

        {viaje && (
          <ViajeEnCurso viaje={viaje}>
            <AvanceViaje key={`${viaje.id}-${viaje.estado}`} viaje={viaje} avanzar={avanzar} />
          </ViajeEnCurso>
        )}

        {avisoChat && (
          <p className="aviso" role="status">
            {`Nuevo mensaje de ${avisoChat.autor}: ${avisoChat.texto}`}{' '}
            <button type="button" onClick={verChat}>
              Abrir chat
            </button>
          </p>
        )}

        {perfil.fila && (
          <div className="tarjeta" role="status">
            <h2>Fila del aeropuerto</h2>
            <p>
              {perfil.fila.posicion === 1 ? 'Eres el primero' : `Vas en el lugar ${perfil.fila.posicion}`} de {perfil.fila.total} · {perfil.fila.zona}
            </p>
            <p className="secundario">Sales de la fila si dejas la zona, terminas el turno o te asignan un viaje.</p>
          </div>
        )}

        {hayViaje ? (
          <div className="resumen-compacto">
            <div className="tarjeta compacta">
              <div className="fila-compacta">
                <h2>Turno</h2>
                <span>
                  {ESTADOS[perfil.estado]} · {perfil.vehiculo_activo?.patente ?? 'Sin declarar'}
                </span>
              </div>
              {falla && (
                <p className="error" role="alert">
                  {falla}
                </p>
              )}
            </div>

            <div className="tarjeta compacta" aria-live="polite">
              <div className="fila-compacta">
                <h2>Ubicación</h2>
                {!enTurno ? (
                  <span className="secundario">No disponible</span>
                ) : rastreo.error === 'permiso' ? (
                  <span className="campo-error">Sin permiso</span>
                ) : rastreo.error ? (
                  <span className="campo-error">Error GPS</span>
                ) : rastreo.activo ? (
                  <span className="ok etiqueta-compacta">
                    GPS activo ({perfil.estado === 'EN_VIAJE' ? '10 s' : '30 s'})
                    {envio.ultimoEnvio ? ` · ${horaDeChile(envio.ultimoEnvio)}` : ''}
                  </span>
                ) : (
                  <span className="secundario">Iniciando GPS…</span>
                )}
              </div>
              {enTurno && rastreo.error === 'permiso' && (
                <p className="error" role="alert">
                  Falta el permiso de ubicación.{' '}
                  <button type="button" onClick={abrirAjustes}>
                    Abrir ajustes
                  </button>
                </p>
              )}
              {enTurno && rastreo.activo && envio.error === 'sin_conexion' && (
                <p className="aviso">Sin conexión: {envio.pendientes} posiciones esperan para enviarse.</p>
              )}
            </div>
          </div>
        ) : (
          <>
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
          </>
        )}

        <div className="acciones">
          <button type="button" className="principal" onClick={verChat}>
            {noLeidos > 0 ? `Chat (${noLeidos} sin leer)` : 'Chat'}
          </button>
          <button type="button" onClick={verMiTurno}>
            Mi turno
          </button>
          <button type="button" onClick={() => (confirmarSalida ? cerrarSesion() : setConfirmarSalida(true))}>
            {confirmarSalida ? (enTurno ? 'Confirmar: se detiene el GPS' : 'Confirmar cierre') : 'Cerrar sesión'}
          </button>
        </div>
      </main>
    </DeslizarParaActualizar>
  );
}
