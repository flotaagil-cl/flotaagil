/**
 * Chat de trabajo del panel (HU-61, HU-62): hilos centrales con cada conductor, directos y grupos del personal.
 * En el escritorio se ven la bandeja y el hilo lado a lado; en el teléfono, uno a la vez.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Boton } from '../../diseno/Boton';
import { Campo, Casilla } from '../../diseno/Campo';
import { claseBoton, iniciales } from '../../diseno/clases';
import { Dialogo } from '../../diseno/Dialogo';
import { Avatar, Insignia } from '../../diseno/Tarjeta';
import { FallaDeCarga } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { useSesion } from '../../sesion/SesionProvider';
import {
  MAX_TEXTO,
  mensajeDelChat,
  useConversacionesChat,
  useEscribir,
  useMarcarLeido,
  useMensajes,
  useNuevoDirecto,
  useNuevoGrupo,
  usePersonal,
  type ConversacionChat,
} from '../api';
import { avisosDisponibles } from '../avisos';
import c from '../chat.module.css';
import { GestionGrupo } from './GestionGrupo';

const TIPO: Record<ConversacionChat['tipo'], string> = {
  CENTRAL: 'Conductor',
  DIRECTO: 'Directo',
  GRUPO: 'Grupo',
  VIAJE: 'Viaje',
  SOPORTE: 'Soporte',
};

export function Chat() {
  const { id } = useParams();
  const activa = id && /^\d+$/.test(id) ? Number(id) : null;
  const { estado } = useSesion();
  const administrador = estado.fase === 'autenticada' && estado.usuario.rol === 'ADMINISTRADOR';
  const consulta = useConversacionesChat();

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Chat</h1>
        <div className={c.botones}>
          <ActivarAvisos />
          {administrador && (
            <Link to="/chat/moderacion" className={claseBoton('secundario')}>
              Moderación de grupos
            </Link>
          )}
        </div>
      </div>
      {consulta.isPending ? (
        <Cargando />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="el chat" reintentar={() => void consulta.refetch()} />
      ) : (
        <div className={c.columnas} data-con-hilo={activa !== null}>
          <Bandeja conversaciones={consulta.data} activa={activa} />
          <div className={c.hilo}>
            {activa === null ? (
              <p className={c.vacio}>Elige una conversación o empieza una nueva.</p>
            ) : (
              <Hilo key={activa} id={activa} conversacion={consulta.data.find((x) => x.id === activa) ?? null} />
            )}
          </div>
        </div>
      )}
    </section>
  );
}

/** HU-63: el navegador pide el permiso solo tras un clic; sin él, los avisos quedan en la pantalla con sonido. */
function ActivarAvisos() {
  const [permiso, setPermiso] = useState(() => (avisosDisponibles() ? Notification.permission : 'denied'));
  if (permiso !== 'default') return null;
  return (
    <Boton variante="secundario" onClick={() => void Notification.requestPermission().then(setPermiso)}>
      Activar avisos del navegador
    </Boton>
  );
}

function Bandeja({ conversaciones, activa }: { conversaciones: ConversacionChat[]; activa: number | null }) {
  const [dialogo, setDialogo] = useState<'directo' | 'grupo' | null>(null);
  return (
    <div className={c.bandeja}>
      <div className={c.botones}>
        <Boton variante="secundario" onClick={() => setDialogo('directo')}>
          Nuevo directo
        </Boton>
        <Boton variante="secundario" onClick={() => setDialogo('grupo')}>
          Nuevo grupo
        </Boton>
      </div>
      {conversaciones.length === 0 ? (
        <p className={c.vacio}>Aún no hay conversaciones.</p>
      ) : (
        <ul className={c.lista} aria-label="Conversaciones">
          {conversaciones.map((conversacion) => (
            <li key={conversacion.id}>
              <Link to={`/chat/${conversacion.id}`} className={c.item} aria-current={conversacion.id === activa ? 'page' : undefined}>
                <Avatar texto={iniciales(conversacion.titulo)} />
                <span className={c.itemTexto}>
                  <span className={c.itemTitulo}>{conversacion.titulo}</span>
                  <span className={c.itemUltimo}>
                    {TIPO[conversacion.tipo]}
                    {conversacion.ultimo && ` · ${conversacion.ultimo.autor}: ${conversacion.ultimo.texto}`}
                  </span>
                </span>
                {conversacion.no_leidos > 0 && <Insignia>{`${conversacion.no_leidos} sin leer`}</Insignia>}
              </Link>
            </li>
          ))}
        </ul>
      )}
      <NuevoDirecto abierto={dialogo === 'directo'} cerrar={() => setDialogo(null)} />
      <NuevoGrupo abierto={dialogo === 'grupo'} cerrar={() => setDialogo(null)} />
    </div>
  );
}

function Hilo({ id, conversacion }: { id: number; conversacion: ConversacionChat | null }) {
  const mensajes = useMensajes(id);
  const marcar = useMarcarLeido(id);
  const marcado = useRef(0);
  const [gestionar, setGestionar] = useState(false);
  const navegar = useNavigate();
  const paginas = mensajes.data?.pages ?? [];
  const lista = [...paginas].reverse().flatMap((p) => p.results);
  const ultimo = lista.at(-1);
  const leidoHasta = paginas[0]?.leido_por_otros_hasta ?? 0;

  // Al ver el último mensaje ajeno, se marca leído (una vez por mensaje).
  useEffect(() => {
    if (ultimo && !ultimo.propio && ultimo.id > marcado.current) {
      marcado.current = ultimo.id;
      marcar.mutate(ultimo.id);
    }
  }, [ultimo, marcar]);

  if (mensajes.isPending) return <Cargando />;
  if (mensajes.isError) {
    if (mensajes.error instanceof ErrorApi && mensajes.error.estado === 404) return <p className={c.vacio}>Esa conversación no existe o ya no participas en ella.</p>;
    return <FallaDeCarga error={mensajes.error} que="los mensajes" reintentar={() => void mensajes.refetch()} />;
  }
  return (
    <>
      <div className={c.cabeceraHilo}>
        <h2>{conversacion?.titulo ?? 'Conversación'}</h2>
        <div className={c.botones}>
          <Link to="/chat" className={claseBoton('texto')}>
            Volver
          </Link>
          {conversacion?.puede_gestionar && (
            <Boton variante="secundario" onClick={() => setGestionar(true)}>
              Gestionar grupo
            </Boton>
          )}
        </div>
      </div>
      {conversacion?.tipo === 'CENTRAL' && <p className={estilos.explicacion}>El conductor ve los mensajes del equipo como «Central»; aquí se ve quién escribió.</p>}
      <ol className={c.mensajes} aria-label="Mensajes">
        {mensajes.hasNextPage && (
          <li>
            <Boton variante="texto" cargando={mensajes.isFetchingNextPage} onClick={() => void mensajes.fetchNextPage()}>
              Ver mensajes anteriores
            </Boton>
          </li>
        )}
        {lista.length === 0 && <li className={c.vacio}>Aún no hay mensajes.</li>}
        {lista.map((mensaje) => (
          <li key={mensaje.id} className={mensaje.propio ? c.propio : c.ajeno}>
            {!mensaje.propio && <span className={c.autor}>{mensaje.autor}</span>}
            <p className={c.cuerpo}>{mensaje.texto}</p>
            <span className={c.detalle}>
              {formatearFechaHora(mensaje.creado_en)}
              {mensaje.propio && ` · ${mensaje.id <= leidoHasta ? 'Leído' : 'Enviado'}`}
            </span>
          </li>
        ))}
      </ol>
      <Escribir id={id} />
      {conversacion?.puede_gestionar && (
        <GestionGrupo
          id={id}
          abierto={gestionar}
          cerrar={() => setGestionar(false)}
          puedeAgregar
          puedeBorrar={conversacion.puede_borrar}
          alSalir={() => navegar('/chat')}
        />
      )}
    </>
  );
}

function Escribir({ id }: { id: number }) {
  const escribir = useEscribir(id);
  const [texto, setTexto] = useState('');
  const [falla, setFalla] = useState<string | null>(null);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const limpio = texto.trim();
    if (!limpio) return;
    setFalla(null);
    try {
      await escribir.mutateAsync({ texto: limpio });
      setTexto('');
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  return (
    <form className={c.escribir} onSubmit={(evento) => void enviar(evento)} noValidate>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <label htmlFor={`mensaje-${id}`} className="solo-lector">
        Mensaje
      </label>
      <textarea id={`mensaje-${id}`} className={c.area} maxLength={MAX_TEXTO} value={texto} placeholder="Escribe un mensaje" onChange={(e) => setTexto(e.target.value)} />
      <div className={c.pie}>
        <span className={c.detalle} aria-live="polite">{`${texto.length}/${MAX_TEXTO}`}</span>
        <Boton type="submit" cargando={escribir.isPending} disabled={!texto.trim()}>
          Enviar
        </Boton>
      </div>
    </form>
  );
}

function NuevoDirecto({ abierto, cerrar }: { abierto: boolean; cerrar: () => void }) {
  const personal = usePersonal(abierto);
  const crear = useNuevoDirecto();
  const navegar = useNavigate();
  const [falla, setFalla] = useState<string | null>(null);

  async function abrir(usuario: number) {
    setFalla(null);
    try {
      const conversacion = await crear.mutateAsync(usuario);
      cerrar();
      navegar(`/chat/${conversacion.id}`);
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  return (
    <Dialogo abierto={abierto} titulo="Nuevo directo" onCerrar={cerrar}>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {personal.isPending ? (
        <Cargando />
      ) : (
        <ul className={c.personas} aria-label="Personal">
          {(personal.data ?? []).map((persona) => (
            <li key={persona.id} className={c.integrante}>
              <span>{persona.nombre}</span>
              <Boton variante="texto" disabled={crear.isPending} onClick={() => void abrir(persona.id)}>
                {`Escribir a ${persona.nombre}`}
              </Boton>
            </li>
          ))}
        </ul>
      )}
    </Dialogo>
  );
}

function NuevoGrupo({ abierto, cerrar }: { abierto: boolean; cerrar: () => void }) {
  const personal = usePersonal(abierto);
  const crear = useNuevoGrupo();
  const navegar = useNavigate();
  const [nombre, setNombre] = useState('');
  const [elegidos, setElegidos] = useState<number[]>([]);
  const [falla, setFalla] = useState<string | null>(null);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (!nombre.trim() || !elegidos.length) {
      setFalla('Ponle un nombre al grupo y elige al menos a una persona.');
      return;
    }
    setFalla(null);
    try {
      const grupo = await crear.mutateAsync({ nombre: nombre.trim(), ids_integrantes: elegidos });
      setNombre('');
      setElegidos([]);
      cerrar();
      navegar(`/chat/${grupo.id}`);
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  return (
    <Dialogo abierto={abierto} titulo="Nuevo grupo" onCerrar={cerrar}>
      <form onSubmit={(evento) => void enviar(evento)} noValidate>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <Campo etiqueta="Nombre del grupo" maxLength={60} value={nombre} onChange={(e) => setNombre(e.target.value)} />
        <fieldset className={c.personas}>
          <legend>Integrantes</legend>
          {(personal.data ?? []).map((persona) => (
            <Casilla
              key={persona.id}
              checked={elegidos.includes(persona.id)}
              onChange={(e) => setElegidos((actual) => (e.target.checked ? [...actual, persona.id] : actual.filter((x) => x !== persona.id)))}
            >
              {persona.nombre}
            </Casilla>
          ))}
        </fieldset>
        <Boton type="submit" cargando={crear.isPending}>
          Crear grupo
        </Boton>
      </form>
    </Dialogo>
  );
}
