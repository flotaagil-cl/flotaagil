/**
 * Chat de la app (HU-61, HU-62): la Central, directos y grupos del personal. Respuestas rápidas y, con un viaje en
 * curso, el aviso «Evita escribir mientras manejas» (no bloquea). Los cambios llegan por el canal en vivo.
 */

import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { useAtras } from '../atras';
import type { CanalChat, MensajeChat } from '../chat/canal';
import { RAPIDAS } from '../chat/rapidas';
import { DeslizarParaActualizar } from '../componentes/DeslizarParaActualizar';
import { Icono } from '../componentes/Icono';
import { fechaYHora } from '../hora';
import { ErrorApi, SinRed } from '../sesion/sesion';

export interface ConversacionChat {
  id: number;
  tipo: 'CENTRAL' | 'DIRECTO' | 'GRUPO' | 'VIAJE' | 'SOPORTE';
  titulo: string;
  no_leidos: number;
  ultimo: { texto: string; autor: string; creado_en: string } | null;
  /** HU-66: el chat con el pasajero queda en solo lectura al terminar el viaje. */
  puede_escribir?: boolean;
}

interface Pagina {
  results: MensajeChat[];
  hay_mas: boolean;
  leido_por_otros_hasta: number;
}

interface Persona {
  id: number;
  nombre: string;
}

export type Pedir = <T>(metodo: 'GET' | 'POST', ruta: string, cuerpo?: unknown) => Promise<T>;

interface Props {
  pedir: Pedir;
  canal: Pick<CanalChat, 'alEvento'>;
  enViaje: boolean;
  volver: () => void;
  /** HU-66: el viaje en curso, para abrir el chat con su pasajero. */
  viajeId?: number | null;
}

const MAX_TEXTO = 1000;

function mensajeDeError(error: unknown): string {
  if (error instanceof SinRed) return 'Sin conexión con el servidor. Intenta de nuevo.';
  if (error instanceof ErrorApi && error.estado === 429) return 'Estás enviando muchos mensajes seguidos. Espera un momento.';
  if (error instanceof ErrorApi && error.message) return error.message;
  return 'No se pudo completar la acción.';
}

/** Une listas de mensajes sin duplicar por ID, en orden cronológico. */
function combinarMensajes(actuales: MensajeChat[], nuevos: MensajeChat[]): MensajeChat[] {
  const porId = new Map<number, MensajeChat>();
  for (const m of actuales) porId.set(m.id, m);
  for (const m of nuevos) porId.set(m.id, m);
  return [...porId.values()].sort((a, b) => a.id - b.id);
}

/** Devuelve hasta 2 iniciales en mayúsculas para avatares circulares. */
function iniciales(texto: string): string {
  return texto
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? '')
    .join('');
}

function AvatarConversacion({ tipo, titulo }: { tipo: ConversacionChat['tipo']; titulo: string }) {
  if (tipo === 'CENTRAL') {
    return (
      <span className="chat-avatar chat-avatar-central" aria-hidden="true">
        <Icono nombre="auto" tamano={18} />
      </span>
    );
  }
  if (tipo === 'GRUPO') {
    return (
      <span className="chat-avatar chat-avatar-grupo" aria-hidden="true">
        <Icono nombre="usuarios" tamano={18} />
      </span>
    );
  }
  return (
    <span className="chat-avatar" aria-hidden="true">
      {iniciales(titulo)}
    </span>
  );
}

type Vista = { tipo: 'lista' } | { tipo: 'hilo'; conversacion: ConversacionChat } | { tipo: 'directo' } | { tipo: 'grupo' };

export function Chat({ pedir, canal, enViaje, volver, viajeId }: Props) {
  const [vista, setVista] = useState<Vista>({ tipo: 'lista' });
  const abrir = (conversacion: ConversacionChat) => setVista({ tipo: 'hilo', conversacion });
  const aLista = () => setVista({ tipo: 'lista' });
  const avisoManejo = enViaje ? (
    <div className="aviso alerta-bloque chat-aviso-manejo" role="status">
      <Icono nombre="alerta" tamano={18} />
      <span>Evita escribir mientras manejas. Usa las respuestas rápidas o detente en un lugar seguro.</span>
    </div>
  ) : null;

  return (
    <main className="app-pantalla">
      {vista.tipo === 'lista' && (
        <Lista pedir={pedir} canal={canal} avisoManejo={avisoManejo} abrir={abrir} nuevo={(tipo) => setVista({ tipo })} volver={volver} viajeId={viajeId} />
      )}
      {vista.tipo === 'hilo' && <Hilo pedir={pedir} canal={canal} avisoManejo={avisoManejo} conversacion={vista.conversacion} volver={aLista} />}
      {(vista.tipo === 'directo' || vista.tipo === 'grupo') && (
        <Nuevo pedir={pedir} tipo={vista.tipo} avisoManejo={avisoManejo} abrir={abrir} volver={aLista} />
      )}
    </main>
  );
}

function Lista({
  pedir,
  canal,
  avisoManejo,
  abrir,
  nuevo,
  volver,
  viajeId,
}: Pick<Props, 'pedir' | 'canal' | 'volver' | 'viajeId'> & {
  avisoManejo: ReactNode;
  abrir: (c: ConversacionChat) => void;
  nuevo: (tipo: 'directo' | 'grupo') => void;
}) {
  const [conversaciones, setConversaciones] = useState<ConversacionChat[] | null>(null);
  const [falla, setFalla] = useState<string | null>(null);

  useAtras(volver);

  const cargar = useCallback(async () => {
    try {
      setConversaciones(await pedir<ConversacionChat[]>('GET', '/api/chat/conversaciones/'));
      setFalla(null);
    } catch (error) {
      setFalla(mensajeDeError(error));
    }
  }, [pedir]);

  useEffect(() => {
    void cargar();
    return canal.alEvento(() => void cargar());
  }, [cargar, canal]);

  /** HU-66: abre (o crea) el chat del viaje en curso con su pasajero. */
  async function conPasajero(viaje: number) {
    try {
      abrir(await pedir<ConversacionChat>('POST', `/api/chat/viajes/${viaje}/`));
    } catch (error) {
      setFalla(mensajeDeError(error));
    }
  }

  return (
    <DeslizarParaActualizar alActualizar={cargar}>
      <div className="app-pantalla-interna">
        <header className="app-barra">
          <button type="button" className="barra-atras" aria-label="Volver al inicio" onClick={volver}>
            <Icono nombre="atras" tamano={22} />
          </button>
          <div className="barra-titulos">
            <h1>Chat</h1>
            <p className="barra-subtitulo">Conversaciones del equipo</p>
          </div>
        </header>

        <div className="app-cuerpo">
          {avisoManejo}
          {falla && (
            <div className="error alerta-bloque" role="alert">
              <Icono nombre="alerta" tamano={18} />
              <div className="alerta-cuerpo">
                <p className="alerta-texto">{falla}</p>
                <button type="button" className="alerta-accion" onClick={() => void cargar()}>
                  Reintentar
                </button>
              </div>
            </div>
          )}
          {conversaciones === null ? (
            !falla && (
              <div className="tarjeta estado-vacio">
                <p className="secundario">Cargando…</p>
              </div>
            )
          ) : (
            <ul className="conversaciones" aria-label="Conversaciones">
              {conversaciones.map((c) => (
                <li key={c.id}>
                  <button type="button" className="conversacion" onClick={() => abrir(c)}>
                    <AvatarConversacion tipo={c.tipo} titulo={c.titulo} />
                    <span className="conversacion-texto">
                      <strong>{c.titulo}</strong>
                      {c.ultimo && <span className="conversacion-ultimo">{`${c.ultimo.autor}: ${c.ultimo.texto}`}</span>}
                    </span>
                    <span className="conversacion-meta">
                      {c.no_leidos > 0 && (
                        <span className="insignia">
                          <Icono nombre="mensaje" tamano={13} />
                          {`${c.no_leidos} sin leer`}
                        </span>
                      )}
                      <Icono nombre="derecha" tamano={18} className="lista-flecha" />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <footer className="app-pie-barra">
          {viajeId && (
            <button type="button" className="principal pie-boton-principal" onClick={() => void conPasajero(viajeId)}>
              <Icono nombre="mensaje" tamano={18} />
              <span>Chat con el pasajero</span>
            </button>
          )}
          <div className="pie-doble">
            <button type="button" className="pie-boton-secundario" onClick={() => nuevo('directo')}>
              <Icono nombre="usuario" tamano={18} />
              <span>Nuevo directo</span>
            </button>
            <button type="button" className="pie-boton-secundario" onClick={() => nuevo('grupo')}>
              <Icono nombre="usuarios" tamano={18} />
              <span>Nuevo grupo</span>
            </button>
          </div>
        </footer>
      </div>
    </DeslizarParaActualizar>
  );
}

function Hilo({
  pedir,
  canal,
  avisoManejo,
  conversacion,
  volver,
}: Pick<Props, 'pedir' | 'canal'> & { avisoManejo: ReactNode; conversacion: ConversacionChat; volver: () => void }) {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([]);
  const [hayMas, setHayMas] = useState(false);
  const [leidoHasta, setLeidoHasta] = useState(0);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [falla, setFalla] = useState<string | null>(null);
  const finRef = useRef<HTMLDivElement | null>(null);
  const ultimoVisto = useRef<number | null>(null);
  const base = `/api/chat/conversaciones/${conversacion.id}`;

  useAtras(volver);

  const cargar = useCallback(async () => {
    try {
      const pagina = await pedir<Pagina>('GET', `${base}/mensajes/`);
      setMensajes((actuales) => combinarMensajes(actuales, pagina.results));
      setLeidoHasta(pagina.leido_por_otros_hasta);
      setHayMas((antes) => antes || pagina.hay_mas);
      const ultimo = pagina.results.at(-1);
      if (ultimo && !ultimo.propio) void pedir('POST', `${base}/leido/`, { hasta: ultimo.id }).catch(() => undefined);
    } catch (error) {
      setFalla(mensajeDeError(error));
    }
  }, [pedir, base]);

  useEffect(() => {
    void cargar();
    return canal.alEvento((evento) => {
      if (evento.tipo === 'mensaje' && evento.mensaje.conversacion === conversacion.id) {
        setMensajes((actuales) => combinarMensajes(actuales, [evento.mensaje]));
        if (!evento.mensaje.propio) void pedir('POST', `${base}/leido/`, { hasta: evento.mensaje.id }).catch(() => undefined);
        return;
      }
      if ((evento.tipo === 'leido' && evento.conversacion === conversacion.id) || evento.tipo === 'inicial') void cargar();
    });
  }, [cargar, canal, conversacion.id, pedir, base]);

  const ultimoId = mensajes.at(-1)?.id ?? null;
  useEffect(() => {
    if (ultimoId === null || ultimoId === ultimoVisto.current) return;
    ultimoVisto.current = ultimoId;
    finRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'end' });
  }, [ultimoId]);

  async function anteriores() {
    try {
      const pagina = await pedir<Pagina>('GET', `${base}/mensajes/?antes=${mensajes[0].id}`);
      setMensajes((actuales) => combinarMensajes(pagina.results, actuales));
      setHayMas(pagina.hay_mas);
    } catch (error) {
      setFalla(mensajeDeError(error));
    }
  }

  async function enviar(cuerpo: { texto?: string; rapida?: string }) {
    setEnviando(true);
    setFalla(null);
    try {
      await pedir('POST', `${base}/mensajes/`, cuerpo);
      if (cuerpo.texto) setTexto('');
      await cargar();
    } catch (error) {
      setFalla(mensajeDeError(error));
    } finally {
      setEnviando(false);
    }
  }

  function alEnviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (texto.trim()) void enviar({ texto: texto.trim() });
  }

  return (
    <div className="app-pantalla-interna chat-hilo">
      <header className="app-barra">
        <button type="button" className="barra-atras" aria-label="Volver a las conversaciones" onClick={volver}>
          <Icono nombre="atras" tamano={22} />
        </button>
        <div className="barra-marca">
          <AvatarConversacion tipo={conversacion.tipo} titulo={conversacion.titulo} />
          <div className="barra-titulos">
            <h1>{conversacion.titulo}</h1>
          </div>
        </div>
      </header>

      <div className="app-cuerpo chat-hilo-cuerpo">
        {avisoManejo}
        {hayMas && mensajes.length > 0 && (
          <button type="button" className="chat-anteriores" onClick={() => void anteriores()}>
            Ver mensajes anteriores
          </button>
        )}
        <ol className="mensajes" aria-label="Mensajes">
          {mensajes.length === 0 && <li className="estado-vacio-item secundario">Aún no hay mensajes.</li>}
          {mensajes.map((m) => (
            <li key={m.id} className={m.propio ? 'propio' : 'ajeno'}>
              {!m.propio && <strong className="mensaje-autor">{m.autor}</strong>}
              <p>{m.texto}</p>
              <span className="mensaje-meta">
                {fechaYHora(m.creado_en)}
                {m.propio && ` · ${m.id <= leidoHasta ? 'Leído' : 'Enviado'}`}
              </span>
            </li>
          ))}
        </ol>
        <div ref={finRef} />
        {falla && (
          <div className="error alerta-bloque" role="alert">
            <Icono nombre="alerta" tamano={18} />
            <span>{falla}</span>
          </div>
        )}
      </div>

      <footer className="app-pie-barra chat-compositor">
        {conversacion.puede_escribir === false ? (
          <p className="chat-solo-lectura">
            <Icono nombre="candado" tamano={16} />
            <span>El viaje terminó: este chat queda en solo lectura.</span>
          </p>
        ) : (
          <>
            <div className="rapidas" role="group" aria-label="Respuestas rápidas">
              {RAPIDAS.map((r) => (
                <button key={r.codigo} type="button" className="chip-rapida" disabled={enviando} onClick={() => void enviar({ rapida: r.codigo })}>
                  {r.texto}
                </button>
              ))}
            </div>
            <form onSubmit={alEnviar} className="chat-form-envio">
              <label htmlFor="mensaje-chat" className="solo-lector">
                Mensaje
              </label>
              <div className="chat-caja-texto">
                <textarea
                  id="mensaje-chat"
                  rows={2}
                  placeholder="Escribe un mensaje…"
                  maxLength={MAX_TEXTO}
                  value={texto}
                  onChange={(e) => setTexto(e.target.value)}
                />
                <div className="chat-caja-pie">
                  <span className="secundario">{`${texto.length}/${MAX_TEXTO}`}</span>
                  <button className="principal chat-enviar" type="submit" disabled={enviando || !texto.trim()}>
                    <Icono nombre="enviar" tamano={16} />
                    <span>Enviar</span>
                  </button>
                </div>
              </div>
            </form>
          </>
        )}
      </footer>
    </div>
  );
}

function Nuevo({
  pedir,
  tipo,
  avisoManejo,
  abrir,
  volver,
}: Pick<Props, 'pedir'> & { tipo: 'directo' | 'grupo'; avisoManejo: ReactNode; abrir: (c: ConversacionChat) => void; volver: () => void }) {
  const [personal, setPersonal] = useState<Persona[] | null>(null);
  const [nombre, setNombre] = useState('');
  const [elegidos, setElegidos] = useState<number[]>([]);
  const [falla, setFalla] = useState<string | null>(null);

  useAtras(volver);

  useEffect(() => {
    pedir<Persona[]>('GET', '/api/chat/personal/').then(setPersonal, (error: unknown) => setFalla(mensajeDeError(error)));
  }, [pedir]);

  async function directo(persona: Persona) {
    try {
      abrir(await pedir<ConversacionChat>('POST', '/api/chat/directos/', { usuario: persona.id }));
    } catch (error) {
      setFalla(mensajeDeError(error));
    }
  }

  async function grupo(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!nombre.trim() || !elegidos.length) {
      setFalla('Ponle un nombre al grupo y elige al menos a una persona.');
      return;
    }
    try {
      const creado = await pedir<{ id: number; nombre: string }>('POST', '/api/chat/grupos/', { nombre: nombre.trim(), ids_integrantes: elegidos });
      abrir({ id: creado.id, tipo: 'GRUPO', titulo: creado.nombre, no_leidos: 0, ultimo: null });
    } catch (error) {
      setFalla(mensajeDeError(error));
    }
  }

  return (
    <div className="app-pantalla-interna">
      <header className="app-barra">
        <button type="button" className="barra-atras" aria-label="Volver a las conversaciones" onClick={volver}>
          <Icono nombre="atras" tamano={22} />
        </button>
        <div className="barra-titulos">
          <h1>{tipo === 'directo' ? 'Nuevo directo' : 'Nuevo grupo'}</h1>
          <p className="barra-subtitulo">{tipo === 'directo' ? 'Elige a una persona del equipo' : 'Define un nombre y elige integrantes'}</p>
        </div>
      </header>

      {tipo === 'directo' ? (
        <div className="app-cuerpo">
          {avisoManejo}
          {falla && (
            <div className="error alerta-bloque" role="alert">
              <Icono nombre="alerta" tamano={18} />
              <span>{falla}</span>
            </div>
          )}
          {personal === null ? (
            !falla && (
              <div className="tarjeta estado-vacio">
                <p className="secundario">Cargando…</p>
              </div>
            )
          ) : (
            <ul className="conversaciones" aria-label="Personal">
              {personal.map((p) => (
                <li key={p.id}>
                  <button type="button" className="conversacion" aria-label={`Escribir a ${p.nombre}`} onClick={() => void directo(p)}>
                    <span className="chat-avatar" aria-hidden="true">
                      {iniciales(p.nombre)}
                    </span>
                    <span className="contacto-nombre">{p.nombre}</span>
                    <Icono nombre="derecha" tamano={18} className="lista-flecha" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
        <form className="chat-form-pantalla" onSubmit={(e) => void grupo(e)}>
          <div className="app-cuerpo">
            {avisoManejo}
            {falla && (
              <div className="error alerta-bloque" role="alert">
                <Icono nombre="alerta" tamano={18} />
                <span>{falla}</span>
              </div>
            )}
            {personal === null ? (
              !falla && (
                <div className="tarjeta estado-vacio">
                  <p className="secundario">Cargando…</p>
                </div>
              )
            ) : (
              <div className="tarjeta grupo-tarjeta">
                <div className="login-campo">
                  <label htmlFor="nombre-grupo">Nombre del grupo</label>
                  <div className="campo-entrada">
                    <Icono nombre="usuarios" tamano={18} className="campo-entrada-icono" />
                    <input id="nombre-grupo" placeholder="Ej: Turno noche" maxLength={60} value={nombre} onChange={(e) => setNombre(e.target.value)} />
                  </div>
                </div>
                <fieldset className="grupo-integrantes">
                  <legend>Integrantes</legend>
                  {personal.map((p) => (
                    <label key={p.id} className="grupo-opcion">
                      <input
                        type="checkbox"
                        checked={elegidos.includes(p.id)}
                        onChange={(e) => setElegidos((a) => (e.target.checked ? [...a, p.id] : a.filter((x) => x !== p.id)))}
                      />
                      <span className="chat-avatar chat-avatar-chico" data-iniciales={iniciales(p.nombre)} aria-hidden="true" />
                      <span className="grupo-opcion-nombre">{p.nombre}</span>
                    </label>
                  ))}
                </fieldset>
              </div>
            )}
          </div>
          {personal !== null && (
            <footer className="app-pie-barra">
              <button className="principal pie-boton-principal" type="submit">
                Crear grupo
              </button>
            </footer>
          )}
        </form>
      )}
    </div>
  );
}
