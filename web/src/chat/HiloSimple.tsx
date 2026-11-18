/**
 * HU-66: hilo compacto del chat para el portal del pasajero (con su conductor o con soporte). Marca leído el último
 * mensaje ajeno y, si la conversación ya no admite mensajes (viaje terminado), queda en solo lectura.
 */

import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Boton } from '../diseno/Boton';
import e from '../diseno/diseno.module.css';
import { formatearFechaHora } from '../hora/hora';
import { MAX_TEXTO, mensajeDelChat, useEscribir, useMarcarLeido, useMensajes } from './api';
import c from './chat.module.css';

interface Props {
  id: number;
  puedeEscribir: boolean;
  /** Etiqueta del área de texto (accesible). */
  etiqueta?: string;
  /** Texto cuando ya no se puede escribir. */
  soloLectura?: string;
  /** Soporte: el viaje al que se refiere el mensaje (opcional). */
  viaje?: number;
}

export function HiloSimple({ id, puedeEscribir, etiqueta = 'Mensaje', soloLectura = 'Este chat quedó en solo lectura.', viaje }: Props) {
  const mensajes = useMensajes(id);
  const marcar = useMarcarLeido(id);
  const escribir = useEscribir(id);
  const marcado = useRef(0);
  const [texto, setTexto] = useState('');
  const [falla, setFalla] = useState<string | null>(null);
  const lista = [...(mensajes.data?.pages ?? [])].reverse().flatMap((p) => p.results);
  const ultimo = lista.at(-1);
  const leidoHasta = mensajes.data?.pages[0]?.leido_por_otros_hasta ?? 0;

  useEffect(() => {
    if (ultimo && !ultimo.propio && ultimo.id > marcado.current) {
      marcado.current = ultimo.id;
      marcar.mutate(ultimo.id);
    }
  }, [ultimo, marcar]);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const limpio = texto.trim();
    if (!limpio) return;
    setFalla(null);
    try {
      await escribir.mutateAsync({ texto: limpio, ...(viaje ? { viaje } : {}) });
      setTexto('');
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  return (
    <div className={c.hilo}>
      <ol className={c.mensajes} aria-label="Mensajes">
        {mensajes.isPending && <li className={c.vacio}>Cargando…</li>}
        {!mensajes.isPending && lista.length === 0 && <li className={c.vacio}>Aún no hay mensajes.</li>}
        {lista.map((m) => (
          <li key={m.id} className={m.propio ? c.propio : c.ajeno}>
            {!m.propio && <span className={c.autor}>{m.autor}</span>}
            <p className={c.cuerpo}>{m.texto}</p>
            <span className={c.detalle}>
              {formatearFechaHora(m.creado_en)}
              {m.propio && ` · ${m.id <= leidoHasta ? 'Leído' : 'Enviado'}`}
            </span>
          </li>
        ))}
      </ol>
      {puedeEscribir ? (
        <form className={c.escribir} onSubmit={(evento) => void enviar(evento)} noValidate>
          {falla && (
            <p className={e.alerta} role="alert">
              {falla}
            </p>
          )}
          <label htmlFor={`hilo-${id}`} className="solo-lector">
            {etiqueta}
          </label>
          <textarea id={`hilo-${id}`} className={c.area} maxLength={MAX_TEXTO} value={texto} placeholder="Escribe un mensaje" onChange={(ev) => setTexto(ev.target.value)} />
          <div className={c.pie}>
            <span className={c.detalle}>{`${texto.length}/${MAX_TEXTO}`}</span>
            <Boton type="submit" cargando={escribir.isPending} disabled={!texto.trim()}>
              Enviar
            </Boton>
          </div>
        </form>
      ) : (
        <p className={e.nota}>{soloLectura}</p>
      )}
    </div>
  );
}
