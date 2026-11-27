/**
 * Chat de trabajo del panel (HU-61, HU-62): hilos centrales con cada conductor, directos y grupos del personal.
 * En el escritorio se ven la bandeja y el hilo lado a lado; en el teléfono, uno a la vez.
 */

import { useEffect, useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Boton } from '../../diseno/Boton';
import { Campo, Casilla } from '../../diseno/Campo';
import { claseBoton, iniciales } from '../../diseno/clases';
import { Dialogo } from '../../diseno/Dialogo';
import { Icono } from '../../diseno/Icono';
import { Avatar, Insignia } from '../../diseno/Tarjeta';
import { FallaDeCarga } from '../../flota/componentes/comunes';
import { formatearFechaHora, formatearHora } from '../../hora/hora';
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
import { etiquetaRol, normalizarBusqueda } from '../formatos';
import { GestionGrupo } from './GestionGrupo';

const TIPO: Record<ConversacionChat['tipo'], string> = {
  CENTRAL: 'Conductor',
  DIRECTO: 'Directo',
  GRUPO: 'Grupo',
  VIAJE: 'Viaje',
  SOPORTE: 'Soporte',
};

type FiltroBandeja = 'TODOS' | 'NO_LEIDOS' | 'CONDUCTORES' | 'EQUIPO';

const FILTROS: { clave: FiltroBandeja; etiqueta: string }[] = [
  { clave: 'TODOS', etiqueta: 'Todos' },
  { clave: 'NO_LEIDOS', etiqueta: 'Sin leer' },
  { clave: 'CONDUCTORES', etiqueta: 'Conductores' },
  { clave: 'EQUIPO', etiqueta: 'Equipo' },
];

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
            <Link to="/chat/moderacion" className={`${claseBoton('secundario')} ${c.botonCompacto}`}>
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
              <div className={c.hiloVacio}>
                <span className={c.hiloVacioIcono} aria-hidden="true">
                  <Icono nombre="mensaje" tamano={24} />
                </span>
                <p className={c.hiloVacioTitulo}>Elige una conversación o empieza una nueva.</p>
                <p className={c.hiloVacioTexto}>
                  Selecciona un hilo de la izquierda para ver los mensajes o inicia una conversación con el equipo.
                </p>
              </div>
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
    <Boton variante="secundario" className={c.botonCompacto} onClick={() => void Notification.requestPermission().then(setPermiso)}>
      Activar avisos del navegador
    </Boton>
  );
}

function Bandeja({ conversaciones, activa }: { conversaciones: ConversacionChat[]; activa: number | null }) {
  const [dialogo, setDialogo] = useState<'directo' | 'grupo' | null>(null);
  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<FiltroBandeja>('TODOS');

  const sinLeer = useMemo(() => conversaciones.filter((x) => x.no_leidos > 0).length, [conversaciones]);
  const filtradas = useMemo(() => {
    const termino = normalizarBusqueda(busqueda);
    return conversaciones.filter((conv) => {
      if (filtro === 'NO_LEIDOS' && conv.no_leidos === 0) return false;
      if (filtro === 'CONDUCTORES' && conv.tipo !== 'CENTRAL') return false;
      if (filtro === 'EQUIPO' && conv.tipo !== 'DIRECTO' && conv.tipo !== 'GRUPO') return false;
      if (!termino) return true;
      const coincideTitulo = normalizarBusqueda(conv.titulo).includes(termino);
      const coincideUltimo = conv.ultimo ? normalizarBusqueda(`${conv.ultimo.autor} ${conv.ultimo.texto}`).includes(termino) : false;
      return coincideTitulo || coincideUltimo;
    });
  }, [conversaciones, busqueda, filtro]);

  return (
    <div className={c.bandeja}>
      <div className={c.bandejaCabecera}>
        <div className={c.accionesBandeja}>
          <Boton variante="secundario" className={c.botonCompacto} onClick={() => setDialogo('directo')}>
            <Icono nombre="mensaje" tamano={16} />
            Nuevo directo
          </Boton>
          <Boton variante="secundario" className={c.botonCompacto} onClick={() => setDialogo('grupo')}>
            <Icono nombre="usuarios" tamano={16} />
            Nuevo grupo
          </Boton>
        </div>
        {conversaciones.length > 0 && (
          <>
            <div className={c.buscadorCaja}>
              <input
                type="search"
                className={c.buscador}
                aria-label="Buscar conversación"
                placeholder="Buscar conversación..."
                value={busqueda}
                onChange={(e) => setBusqueda(e.target.value)}
              />
            </div>
            <div className={c.filtros} role="group" aria-label="Filtrar conversaciones">
              {FILTROS.map((item) => (
                <button
                  key={item.clave}
                  type="button"
                  className={c.chip}
                  aria-pressed={filtro === item.clave}
                  onClick={() => setFiltro(item.clave)}
                >
                  {item.clave === 'NO_LEIDOS' && sinLeer > 0 ? `${item.etiqueta} (${sinLeer})` : item.etiqueta}
                </button>
              ))}
            </div>
          </>
        )}
      </div>
      {conversaciones.length === 0 ? (
        <p className={c.vacio}>Aún no hay conversaciones.</p>
      ) : filtradas.length === 0 ? (
        <p className={c.vacio}>Ninguna conversación coincide con el filtro.</p>
      ) : (
        <ul className={c.lista} aria-label="Conversaciones">
          {filtradas.map((conversacion) => (
            <li key={conversacion.id}>
              <Link
                to={`/chat/${conversacion.id}`}
                className={c.item}
                aria-current={conversacion.id === activa ? 'page' : undefined}
                data-no-leido={conversacion.no_leidos > 0 ? 'true' : 'false'}
              >
                <Avatar texto={iniciales(conversacion.titulo)} />
                <span className={c.itemTexto}>
                  <span className={c.itemCabecera}>
                    <span className={c.itemTitulo}>{conversacion.titulo}</span>
                    {conversacion.ultimo_mensaje_en && (
                      <span className={c.itemHora}>{formatearHora(conversacion.ultimo_mensaje_en)}</span>
                    )}
                  </span>
                  <span className={c.itemPie}>
                    <span className={c.itemUltimo}>
                      <span className={c.tipoEtiqueta} data-tipo={conversacion.tipo}>
                        {TIPO[conversacion.tipo]}
                      </span>
                      {conversacion.ultimo && (
                        <span className={c.ultimoTexto}>{` · ${conversacion.ultimo.autor}: ${conversacion.ultimo.texto}`}</span>
                      )}
                    </span>
                    {conversacion.no_leidos > 0 && <Insignia>{`${conversacion.no_leidos} sin leer`}</Insignia>}
                  </span>
                </span>
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
  const listaRef = useRef<HTMLOListElement>(null);
  const ultimoEnVista = useRef<number | null>(null);
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

  // Baja al final al abrir el hilo o cuando llega un mensaje nuevo; al paginar hacia arriba conserva la posición.
  useEffect(() => {
    const ultimoId = ultimo?.id ?? null;
    if (ultimoId !== null && ultimoId !== ultimoEnVista.current) {
      ultimoEnVista.current = ultimoId;
      const contenedor = listaRef.current;
      if (contenedor) contenedor.scrollTop = contenedor.scrollHeight;
    }
  }, [ultimo?.id]);

  if (mensajes.isPending) return <Cargando />;
  if (mensajes.isError) {
    if (mensajes.error instanceof ErrorApi && mensajes.error.estado === 404) {
      return <p className={c.vacio}>Esa conversación no existe o ya no participas en ella.</p>;
    }
    return <FallaDeCarga error={mensajes.error} que="los mensajes" reintentar={() => void mensajes.refetch()} />;
  }
  return (
    <>
      <div className={c.cabeceraHilo}>
        <div className={c.cabeceraIdentidad}>
          <Link to="/chat" className={c.volverMovil}>
            <Icono nombre="atras" tamano={16} />
            Volver
          </Link>
          <Avatar texto={iniciales(conversacion?.titulo ?? 'C')} />
          <div>
            <h2>{conversacion?.titulo ?? 'Conversación'}</h2>
            {conversacion && <span className={c.tipoSubtitulo}>{TIPO[conversacion.tipo]}</span>}
          </div>
        </div>
        <div className={c.botones}>
          {conversacion?.puede_gestionar && (
            <Boton variante="secundario" className={c.botonCompacto} onClick={() => setGestionar(true)}>
              Gestionar grupo
            </Boton>
          )}
        </div>
      </div>
      {conversacion?.tipo === 'CENTRAL' && (
        <p className={c.notaCentral}>
          <Icono nombre="info" tamano={15} />
          El conductor ve los mensajes del equipo como «Central»; aquí se ve quién escribió.
        </p>
      )}
      <ol ref={listaRef} className={c.mensajes} aria-label="Mensajes">
        {mensajes.hasNextPage && (
          <li className={c.cargarAnteriores}>
            <Boton variante="texto" cargando={mensajes.isFetchingNextPage} onClick={() => void mensajes.fetchNextPage()}>
              Ver mensajes anteriores
            </Boton>
          </li>
        )}
        {lista.length === 0 && <li className={c.vacio}>Aún no hay mensajes.</li>}
        {lista.map((mensaje) => {
          const leido = mensaje.propio && mensaje.id <= leidoHasta;
          return (
            <li key={mensaje.id} className={mensaje.propio ? c.propio : c.ajeno}>
              {!mensaje.propio && <span className={c.autor}>{mensaje.autor}</span>}
              <p className={c.cuerpo}>{mensaje.texto}</p>
              <span className={c.detalle}>
                {formatearFechaHora(mensaje.creado_en)}
                {mensaje.propio && (
                  <span className={leido ? c.estadoLeido : undefined}>{` · ${leido ? 'Leído' : 'Enviado'}`}</span>
                )}
              </span>
            </li>
          );
        })}
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

  async function enviarMensaje() {
    const limpio = texto.trim();
    if (!limpio || escribir.isPending) return;
    setFalla(null);
    try {
      await escribir.mutateAsync({ texto: limpio });
      setTexto('');
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    void enviarMensaje();
  }

  function alPresionarTecla(evento: KeyboardEvent<HTMLTextAreaElement>) {
    if (evento.key === 'Enter' && !evento.shiftKey && !evento.nativeEvent.isComposing) {
      evento.preventDefault();
      void enviarMensaje();
    }
  }

  return (
    <form className={c.escribir} onSubmit={enviar} noValidate>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <label htmlFor={`mensaje-${id}`} className="solo-lector">
        Mensaje
      </label>
      <div className={c.compositorFila}>
        <textarea
          id={`mensaje-${id}`}
          className={c.area}
          maxLength={MAX_TEXTO}
          value={texto}
          placeholder="Escribe un mensaje"
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={alPresionarTecla}
        />
        <Boton type="submit" className={c.botonEnviar} cargando={escribir.isPending} disabled={!texto.trim()}>
          Enviar
        </Boton>
      </div>
      <div className={c.pie}>
        <span className={c.ayudaTecla}>Enter para enviar · Shift+Enter para nueva línea</span>
        <span className={c.contador} aria-live="polite">{`${texto.length}/${MAX_TEXTO}`}</span>
      </div>
    </form>
  );
}

function NuevoDirecto({ abierto, cerrar }: { abierto: boolean; cerrar: () => void }) {
  const personal = usePersonal(abierto);
  const crear = useNuevoDirecto();
  const navegar = useNavigate();
  const [busqueda, setBusqueda] = useState('');
  const [falla, setFalla] = useState<string | null>(null);

  const personas = useMemo(() => {
    const termino = normalizarBusqueda(busqueda);
    const lista = personal.data ?? [];
    if (!termino) return lista;
    return lista.filter((p) => normalizarBusqueda(`${p.nombre} ${etiquetaRol(p.rol)}`).includes(termino));
  }, [personal.data, busqueda]);

  async function abrir(usuario: number) {
    setFalla(null);
    try {
      const conversacion = await crear.mutateAsync(usuario);
      setBusqueda('');
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
        <div className={c.personasCaja}>
          {(personal.data ?? []).length > 0 && (
            <input
              type="search"
              className={c.buscador}
              aria-label="Buscar persona"
              placeholder="Buscar persona..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
          )}
          {personas.length === 0 ? (
            <p className={c.vacio}>No hay personas que coincidan.</p>
          ) : (
            <ul className={c.personas} aria-label="Personal">
              {personas.map((persona) => (
                <li key={persona.id} className={c.integrante}>
                  <span className={c.personaInfo}>
                    <Avatar texto={iniciales(persona.nombre)} />
                    <span className={c.personaTexto}>
                      <span className={c.personaNombre}>{persona.nombre}</span>
                      <span className={c.personaRol}>{etiquetaRol(persona.rol)}</span>
                    </span>
                  </span>
                  <Boton
                    variante="secundario"
                    className={c.botonFila}
                    aria-label={`Escribir a ${persona.nombre}`}
                    disabled={crear.isPending}
                    onClick={() => void abrir(persona.id)}
                  >
                    Escribir
                  </Boton>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Dialogo>
  );
}

function NuevoGrupo({ abierto, cerrar }: { abierto: boolean; cerrar: () => void }) {
  const personal = usePersonal(abierto);
  const crear = useNuevoGrupo();
  const navegar = useNavigate();
  const [nombre, setNombre] = useState('');
  const [busqueda, setBusqueda] = useState('');
  const [elegidos, setElegidos] = useState<number[]>([]);
  const [falla, setFalla] = useState<string | null>(null);

  const personas = useMemo(() => {
    const termino = normalizarBusqueda(busqueda);
    const lista = personal.data ?? [];
    if (!termino) return lista;
    return lista.filter((p) => normalizarBusqueda(`${p.nombre} ${etiquetaRol(p.rol)}`).includes(termino));
  }, [personal.data, busqueda]);

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
      setBusqueda('');
      setElegidos([]);
      cerrar();
      navegar(`/chat/${grupo.id}`);
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  return (
    <Dialogo abierto={abierto} titulo="Nuevo grupo" onCerrar={cerrar}>
      <form className={c.formularioModal} onSubmit={(evento) => void enviar(evento)} noValidate>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <Campo
          etiqueta="Nombre del grupo"
          placeholder="Ej. Turno noche"
          maxLength={60}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <fieldset className={c.grupoFieldset}>
          <div className={c.grupoLeyendaRow}>
            <legend className={c.grupoLeyenda}>Integrantes</legend>
            <span className={c.grupoContador}>
              {elegidos.length} {elegidos.length === 1 ? 'seleccionado' : 'seleccionados'}
            </span>
          </div>
          {(personal.data ?? []).length > 0 && (
            <input
              type="search"
              className={`${c.buscador} ${c.buscadorGrupo}`}
              aria-label="Filtrar integrantes"
              placeholder="Buscar persona..."
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
            />
          )}
          <div className={c.grupoLista}>
            {personas.length === 0 ? (
              <p className={c.vacio}>No hay personas que coincidan.</p>
            ) : (
              personas.map((persona) => (
                <div key={persona.id} className={c.grupoOpcion}>
                  <Casilla
                    checked={elegidos.includes(persona.id)}
                    onChange={(e) =>
                      setElegidos((actual) => (e.target.checked ? [...actual, persona.id] : actual.filter((x) => x !== persona.id)))
                    }
                  >
                    {persona.nombre}
                  </Casilla>
                </div>
              ))
            )}
          </div>
        </fieldset>
        <div className={c.accionesModal}>
          <Boton variante="secundario" className={c.botonCompacto} onClick={cerrar}>
            Cancelar
          </Boton>
          <Boton type="submit" className={c.botonCompacto} cargando={crear.isPending}>
            Crear grupo
          </Boton>
        </div>
      </form>
    </Dialogo>
  );
}
