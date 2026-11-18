/**
 * Chat de la app (HU-61, HU-62): la Central, directos y grupos del personal. Respuestas rápidas y, con un viaje en
 * curso, el aviso «Evita escribir mientras manejas» (no bloquea). Los cambios llegan por el canal en vivo.
 */

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import type { CanalChat, MensajeChat } from '../chat/canal';
import { RAPIDAS } from '../chat/rapidas';
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

type Vista = { tipo: 'lista' } | { tipo: 'hilo'; conversacion: ConversacionChat } | { tipo: 'directo' } | { tipo: 'grupo' };

export function Chat({ pedir, canal, enViaje, volver, viajeId }: Props) {
  const [vista, setVista] = useState<Vista>({ tipo: 'lista' });
  const abrir = (conversacion: ConversacionChat) => setVista({ tipo: 'hilo', conversacion });
  const aLista = () => setVista({ tipo: 'lista' });

  return (
    <main>
      {enViaje && (
        <p className="aviso" role="status">
          Evita escribir mientras manejas. Usa las respuestas rápidas o detente en un lugar seguro.
        </p>
      )}
      {vista.tipo === 'lista' && <Lista pedir={pedir} canal={canal} abrir={abrir} nuevo={(tipo) => setVista({ tipo })} volver={volver} viajeId={viajeId} />}
      {vista.tipo === 'hilo' && <Hilo pedir={pedir} canal={canal} conversacion={vista.conversacion} volver={aLista} />}
      {(vista.tipo === 'directo' || vista.tipo === 'grupo') && <Nuevo pedir={pedir} tipo={vista.tipo} abrir={abrir} volver={aLista} />}
    </main>
  );
}

function Lista({ pedir, canal, abrir, nuevo, volver, viajeId }: Pick<Props, 'pedir' | 'canal' | 'volver' | 'viajeId'> & { abrir: (c: ConversacionChat) => void; nuevo: (tipo: 'directo' | 'grupo') => void }) {
  const [conversaciones, setConversaciones] = useState<ConversacionChat[] | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
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
    <>
      <h1>Chat</h1>
      {falla && (
        <p className="error" role="alert">
          {falla}{' '}
          <button type="button" onClick={() => void cargar()}>
            Reintentar
          </button>
        </p>
      )}
      {conversaciones === null ? (
        !falla && <p>Cargando…</p>
      ) : (
        <ul className="conversaciones" aria-label="Conversaciones">
          {conversaciones.map((c) => (
            <li key={c.id}>
              <button type="button" className="conversacion" onClick={() => abrir(c)}>
                <strong>{c.titulo}</strong>
                {c.ultimo && <span className="secundario">{`${c.ultimo.autor}: ${c.ultimo.texto}`}</span>}
                {c.no_leidos > 0 && <span className="insignia">{`${c.no_leidos} sin leer`}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="acciones">
        {viajeId && (
          <button type="button" className="principal" onClick={() => void conPasajero(viajeId)}>
            Chat con el pasajero
          </button>
        )}
        <button type="button" onClick={() => nuevo('directo')}>
          Nuevo directo
        </button>
        <button type="button" onClick={() => nuevo('grupo')}>
          Nuevo grupo
        </button>
        <button type="button" onClick={volver}>
          Volver al inicio
        </button>
      </div>
    </>
  );
}

function Hilo({ pedir, canal, conversacion, volver }: Pick<Props, 'pedir' | 'canal'> & { conversacion: ConversacionChat; volver: () => void }) {
  const [mensajes, setMensajes] = useState<MensajeChat[]>([]);
  const [hayMas, setHayMas] = useState(false);
  const [leidoHasta, setLeidoHasta] = useState(0);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [falla, setFalla] = useState<string | null>(null);
  const base = `/api/chat/conversaciones/${conversacion.id}`;

  const cargar = useCallback(async () => {
    try {
      const pagina = await pedir<Pagina>('GET', `${base}/mensajes/`);
      // Se conservan los anteriores ya cargados y se reemplaza la última página.
      setMensajes((actuales) => [...actuales.filter((m) => m.id < (pagina.results[0]?.id ?? Infinity)), ...pagina.results]);
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
      if ((evento.tipo === 'mensaje' && evento.mensaje.conversacion === conversacion.id) || (evento.tipo === 'leido' && evento.conversacion === conversacion.id) || evento.tipo === 'inicial') void cargar();
    });
  }, [cargar, canal, conversacion.id]);

  async function anteriores() {
    try {
      const pagina = await pedir<Pagina>('GET', `${base}/mensajes/?antes=${mensajes[0].id}`);
      setMensajes((actuales) => [...pagina.results, ...actuales]);
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
    <>
      <h1>{conversacion.titulo}</h1>
      <button type="button" onClick={volver}>
        Volver a las conversaciones
      </button>
      {hayMas && mensajes.length > 0 && (
        <button type="button" onClick={() => void anteriores()}>
          Ver mensajes anteriores
        </button>
      )}
      <ol className="mensajes" aria-label="Mensajes">
        {mensajes.length === 0 && <li className="secundario">Aún no hay mensajes.</li>}
        {mensajes.map((m) => (
          <li key={m.id} className={m.propio ? 'propio' : 'ajeno'}>
            {!m.propio && <strong>{m.autor}</strong>}
            <p>{m.texto}</p>
            <span className="secundario">
              {fechaYHora(m.creado_en)}
              {m.propio && ` · ${m.id <= leidoHasta ? 'Leído' : 'Enviado'}`}
            </span>
          </li>
        ))}
      </ol>
      {falla && (
        <p className="error" role="alert">
          {falla}
        </p>
      )}
      {conversacion.puede_escribir === false ? (
        <p className="secundario">El viaje terminó: este chat queda en solo lectura.</p>
      ) : (
        <>
          <div className="rapidas" role="group" aria-label="Respuestas rápidas">
            {RAPIDAS.map((r) => (
              <button key={r.codigo} type="button" disabled={enviando} onClick={() => void enviar({ rapida: r.codigo })}>
                {r.texto}
              </button>
            ))}
          </div>
          <form onSubmit={alEnviar} className="campo">
            <label htmlFor="mensaje-chat">Mensaje</label>
            <textarea id="mensaje-chat" maxLength={MAX_TEXTO} value={texto} onChange={(e) => setTexto(e.target.value)} />
            <span className="secundario">{`${texto.length}/${MAX_TEXTO}`}</span>
            <button className="principal" type="submit" disabled={enviando || !texto.trim()}>
              Enviar
            </button>
          </form>
        </>
      )}
    </>
  );
}

function Nuevo({ pedir, tipo, abrir, volver }: Pick<Props, 'pedir'> & { tipo: 'directo' | 'grupo'; abrir: (c: ConversacionChat) => void; volver: () => void }) {
  const [personal, setPersonal] = useState<Persona[] | null>(null);
  const [nombre, setNombre] = useState('');
  const [elegidos, setElegidos] = useState<number[]>([]);
  const [falla, setFalla] = useState<string | null>(null);

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
    <>
      <h1>{tipo === 'directo' ? 'Nuevo directo' : 'Nuevo grupo'}</h1>
      {falla && (
        <p className="error" role="alert">
          {falla}
        </p>
      )}
      {personal === null ? (
        !falla && <p>Cargando…</p>
      ) : tipo === 'directo' ? (
        <ul className="conversaciones" aria-label="Personal">
          {personal.map((p) => (
            <li key={p.id}>
              <button type="button" className="conversacion" onClick={() => void directo(p)}>
                {`Escribir a ${p.nombre}`}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <form onSubmit={(e) => void grupo(e)}>
          <div className="campo">
            <label htmlFor="nombre-grupo">Nombre del grupo</label>
            <input id="nombre-grupo" maxLength={60} value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </div>
          <fieldset className="vehiculos">
            <legend>Integrantes</legend>
            {personal.map((p) => (
              <label key={p.id} className="opcion">
                <input type="checkbox" checked={elegidos.includes(p.id)} onChange={(e) => setElegidos((a) => (e.target.checked ? [...a, p.id] : a.filter((x) => x !== p.id)))} />
                {p.nombre}
              </label>
            ))}
          </fieldset>
          <button className="principal" type="submit">
            Crear grupo
          </button>
        </form>
      )}
      <button type="button" onClick={volver}>
        Volver a las conversaciones
      </button>
    </>
  );
}
