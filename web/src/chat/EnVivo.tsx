/**
 * Canal en vivo del chat (/ws/chat/, CC-19) para todo el panel: al llegar un mensaje, una lectura o un cambio de
 * conversaciones se vuelven a pedir las consultas del chat. Reconexión y renovación del access, como los indicadores.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { useEntorno } from '../entornoContexto';
import type { CrearSocket } from '../mapa/conexion';
import { ConexionIndicadores, type FaseIndicadores } from '../paginas/conexionIndicadores';
import { useSesion } from '../sesion/SesionProvider';
import { claves } from './api';
import { ContextoChatEnVivo, type ContextoChat, type EventoChat, type OyenteChat } from './enVivoContexto';

export function ChatEnVivo({ children, crearSocket }: { children: ReactNode; crearSocket?: CrearSocket }) {
  const entorno = useEntorno();
  const { sesion } = useSesion();
  const cliente = useQueryClient();
  const [fase, setFase] = useState<FaseIndicadores>('conectando');
  const [oyentes] = useState(() => new Set<OyenteChat>());

  const conexion = useMemo(
    () =>
      new ConexionIndicadores(
        `${entorno.origen.replace(/^http/, 'ws')}/ws/chat/`,
        sesion,
        (dato) => {
          const evento = dato as EventoChat;
          if (evento.tipo === 'pong') return;
          if (evento.tipo === 'mensaje') {
            void cliente.invalidateQueries({ queryKey: claves.conversaciones });
            void cliente.invalidateQueries({ queryKey: claves.mensajes(evento.mensaje.conversacion) });
          } else if (evento.tipo === 'leido') {
            void cliente.invalidateQueries({ queryKey: claves.mensajes(evento.conversacion) });
          } else {
            void cliente.invalidateQueries({ queryKey: claves.todo });
          }
          oyentes.forEach((oyente) => oyente(evento));
        },
        setFase,
        crearSocket,
      ),
    [entorno, sesion, cliente, crearSocket, oyentes],
  );

  useEffect(() => {
    conexion.iniciar();
    return () => conexion.detener();
  }, [conexion]);

  const valor = useMemo<ContextoChat>(
    () => ({
      fase,
      alRecibir: (oyente) => {
        oyentes.add(oyente);
        return () => oyentes.delete(oyente);
      },
    }),
    [fase, oyentes],
  );
  return <ContextoChatEnVivo.Provider value={valor}>{children}</ContextoChatEnVivo.Provider>;
}
