import { useEffect, useState } from 'react';
import type { MensajeChat } from '../chat/canal';
import { DeslizarParaActualizar } from '../componentes/DeslizarParaActualizar';
import { Icono } from '../componentes/Icono';
import { Marca } from '../componentes/Marca';
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
/** CC-27: cada estado se distingue por ícono y texto, no solo por el color. */
const ICONO_ESTADO = { DISPONIBLE: 'check', NO_DISPONIBLE: 'reloj', EN_VIAJE: 'auto' } as const;

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
  /** HU-74: cambiar la contraseña. */
  verPassword: () => void;
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
  verPassword,
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
      <main className="app-pantalla">
        <header className="app-barra">
          <div className="barra-marca">
            <Marca clase="barra-logo" tamano={20} />
            <div className="barra-titulos">
              <h1>Hola, {usuario.nombre}</h1>
              <p className="barra-subtitulo">{usuario.empresa.apariencia?.nombre_marca || usuario.empresa.razon_social}</p>
            </div>
          </div>
          <span className="barra-estado" data-estado={perfil.estado}>
            <Icono nombre={ICONO_ESTADO[perfil.estado]} tamano={14} />
            {ESTADOS[perfil.estado]}
          </span>
        </header>

        <div className="app-cuerpo">
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
            <div className="aviso alerta-bloque" role="status">
              <Icono nombre="mensaje" tamano={18} />
              <div className="alerta-cuerpo">
                <p className="alerta-texto">{`Nuevo mensaje de ${avisoChat.autor}: ${avisoChat.texto}`}</p>
                <button type="button" className="alerta-accion" onClick={verChat}>
                  Abrir chat
                </button>
              </div>
            </div>
          )}

          {perfil.fila && (
            <div className="tarjeta tarjeta-destacada" role="status">
              <div className="tarjeta-cabecera">
                <span className="tarjeta-icono">
                  <Icono nombre="ubicacion" tamano={18} />
                </span>
                <h2>Fila del aeropuerto</h2>
              </div>
              <p className="tarjeta-dato-principal">
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
                  <div className="error alerta-bloque alerta-compacta" role="alert">
                    <Icono nombre="alerta" tamano={18} />
                    <span>{falla}</span>
                  </div>
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
                      <Icono nombre="check" tamano={14} />{' '}
                      GPS activo ({perfil.estado === 'EN_VIAJE' ? '10 s' : '30 s'})
                      {envio.ultimoEnvio ? ` · ${horaDeChile(envio.ultimoEnvio)}` : ''}
                    </span>
                  ) : (
                    <span className="secundario">Iniciando GPS…</span>
                  )}
                </div>
                {enTurno && rastreo.error === 'permiso' && (
                  <div className="error alerta-bloque alerta-compacta" role="alert">
                    <Icono nombre="alerta" tamano={18} />
                    <div className="alerta-cuerpo">
                      <p className="alerta-texto">Falta el permiso de ubicación.</p>
                      <button type="button" className="alerta-accion" onClick={abrirAjustes}>
                        <Icono nombre="configuracion" tamano={16} />
                        <span>Abrir ajustes</span>
                      </button>
                    </div>
                  </div>
                )}
                {enTurno && rastreo.activo && envio.error === 'sin_conexion' && (
                  <div className="aviso alerta-bloque alerta-compacta">
                    <Icono nombre="alerta" tamano={18} />
                    <span>Sin conexión: {envio.pendientes} posiciones esperan para enviarse.</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <>
              <div className="tarjeta">
                <div className="tarjeta-cabecera">
                  <span className="tarjeta-icono">
                    <Icono nombre="reloj" tamano={18} />
                  </span>
                  <h2>Turno</h2>
                </div>
                <dl className="lista-datos">
                  <dt>Estado</dt>
                  <dd>{ESTADOS[perfil.estado]}</dd>
                  <dt>Vehículo</dt>
                  <dd>{perfil.vehiculo_activo?.patente ?? 'Sin declarar'}</dd>
                </dl>
                {falla && (
                  <div className="error alerta-bloque" role="alert">
                    <Icono nombre="alerta" tamano={18} />
                    <span>{falla}</span>
                  </div>
                )}

                {perfil.estado === 'NO_DISPONIBLE' &&
                  (perfil.vehiculos.length === 0 ? (
                    <div className="aviso alerta-bloque">
                      <Icono nombre="alerta" tamano={18} />
                      <span>No tienes vehículos asociados. Habla con el administrador de tu empresa.</span>
                    </div>
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
                {perfil.estado === 'EN_VIAJE' && <p className="secundario nota-turno">Estás en un viaje: el turno sigue hasta terminarlo.</p>}
              </div>

              <div className="tarjeta" aria-live="polite">
                <div className="tarjeta-cabecera">
                  <span className="tarjeta-icono">
                    <Icono nombre="ubicacion" tamano={18} />
                  </span>
                  <h2>Ubicación</h2>
                </div>
                {!enTurno ? (
                  <p className="secundario">No se registra: estás No disponible.</p>
                ) : rastreo.error === 'permiso' ? (
                  <div className="error alerta-bloque" role="alert">
                    <Icono nombre="alerta" tamano={20} />
                    <div className="alerta-cuerpo">
                      <p className="alerta-texto">Falta el permiso de ubicación. Sin él no se puede registrar tu posición en turno.</p>
                      <button type="button" className="alerta-accion" onClick={abrirAjustes}>
                        <Icono nombre="configuracion" tamano={16} />
                        <span>Abrir ajustes</span>
                      </button>
                    </div>
                  </div>
                ) : rastreo.error ? (
                  <div className="error alerta-bloque" role="alert">
                    <Icono nombre="alerta" tamano={20} />
                    <span>No se pudo iniciar el GPS.</span>
                  </div>
                ) : rastreo.activo ? (
                  <>
                    <div className="ok alerta-bloque">
                      <Icono nombre="check" tamano={18} />
                      <span>Registrando tu ubicación ({perfil.estado === 'EN_VIAJE' ? 'cada 10 s' : 'cada 30 s'}).</span>
                    </div>
                    {envio.ultimoEnvio && <p className="secundario dato-gps">Último envío: {horaDeChile(envio.ultimoEnvio)}</p>}
                    {envio.error === 'sin_conexion' && (
                      <div className="aviso alerta-bloque">
                        <Icono nombre="alerta" tamano={18} />
                        <span>Sin conexión: {envio.pendientes} posiciones esperan para enviarse.</span>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="secundario">Iniciando el GPS…</p>
                )}
                {enTurno && (
                  <details className="gps-guia">
                    <summary>
                      <Icono nombre="bateria" tamano={18} />
                      <span>Para que el GPS no se corte con la pantalla apagada</span>
                      <Icono nombre="derecha" tamano={16} className="gps-guia-flecha" />
                    </summary>
                    <ol className="gps-pasos">
                      <li>Ajustes de la app → Ahorro de batería → «Sin restricciones».</li>
                      <li>Activa el inicio automático de la app.</li>
                      <li>En apps recientes, deja la app con candado.</li>
                      <li>Permiso de ubicación con «ubicación precisa».</li>
                    </ol>
                    <button type="button" className="boton-secundario-ancho" onClick={abrirAjustes}>
                      <Icono nombre="configuracion" tamano={18} />
                      <span>Abrir ajustes de la app</span>
                    </button>
                  </details>
                )}
              </div>
            </>
          )}
        </div>

        <nav className="barra-inferior" aria-label="Navegación principal">
          <div className="barra-inferior-grid">
            <button type="button" className="nav-item" aria-label={noLeidos > 0 ? `Chat (${noLeidos} sin leer)` : 'Chat'} onClick={verChat}>
              <span className="nav-icono">
                <Icono nombre="mensaje" tamano={22} />
                {noLeidos > 0 && (
                  <span className="nav-badge" aria-hidden="true">
                    {noLeidos}
                  </span>
                )}
              </span>
              <span className="nav-texto" aria-hidden="true">
                Chat
              </span>
            </button>
            <button type="button" className="nav-item" onClick={verMiTurno}>
              <span className="nav-icono">
                <Icono nombre="caja" tamano={22} />
              </span>
              <span className="nav-texto">Mi turno</span>
            </button>
            <button type="button" className="nav-item" onClick={verPassword}>
              <span className="nav-icono">
                <Icono nombre="llave" tamano={22} />
              </span>
              <span className="nav-texto">Contraseña</span>
            </button>
            <button
              type="button"
              className={confirmarSalida ? 'nav-item nav-peligro' : 'nav-item'}
              onClick={() => (confirmarSalida ? cerrarSesion() : setConfirmarSalida(true))}
            >
              <span className="nav-icono">
                <Icono nombre="salir" tamano={22} />
              </span>
              <span className="nav-texto">{confirmarSalida ? (enTurno ? 'Confirmar: se detiene el GPS' : 'Confirmar cierre') : 'Cerrar sesión'}</span>
            </button>
          </div>
        </nav>
      </main>
    </DeslizarParaActualizar>
  );
}
