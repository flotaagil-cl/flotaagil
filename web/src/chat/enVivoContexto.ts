import { createContext, useContext } from 'react';
import type { FaseIndicadores } from '../paginas/conexionIndicadores';
import type { MensajeChat } from './api';

export type EventoChat =
  | { tipo: 'inicial' }
  | { tipo: 'mensaje'; mensaje: MensajeChat }
  | { tipo: 'leido'; conversacion: number }
  | { tipo: 'conversaciones' }
  | { tipo: 'pong' };

export type OyenteChat = (evento: EventoChat) => void;

export interface ContextoChat {
  fase: FaseIndicadores;
  /** Para los avisos (HU-63): devuelve cómo dejar de escuchar. */
  alRecibir(oyente: OyenteChat): () => void;
}

export const ContextoChatEnVivo = createContext<ContextoChat>({ fase: 'conectando', alRecibir: () => () => undefined });

export function useChatEnVivo(): ContextoChat {
  return useContext(ContextoChatEnVivo);
}
