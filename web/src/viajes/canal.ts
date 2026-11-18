/** HU-65 y HU-66: canal en vivo del pasajero (/ws/chat/): cambios de su viaje y mensajes de sus chats. */

import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useEntorno } from '../entornoContexto';
import { ConexionIndicadores } from '../paginas/conexionIndicadores';
import { useSesion } from '../sesion/SesionProvider';

export interface EventoPasajero {
  tipo?: string;
  viaje?: number;
  conversacion?: number;
  mensaje?: { conversacion: number };
}

/** Abre el canal mientras la pantalla está montada. Los mensajes y lecturas refrescan las consultas del chat. */
export function useCanalPasajero(alEvento?: (evento: EventoPasajero) => void) {
  const entorno = useEntorno();
  const { sesion } = useSesion();
  const cliente = useQueryClient();
  const oyente = useRef(alEvento);
  useEffect(() => {
    oyente.current = alEvento;
  });

  useEffect(() => {
    const conexion = new ConexionIndicadores(
      `${entorno.origen.replace(/^http/, 'ws')}/ws/chat/`,
      sesion,
      (dato) => {
        const evento = dato as EventoPasajero;
        if (evento.tipo === 'mensaje' || evento.tipo === 'leido') void cliente.invalidateQueries({ queryKey: ['chat'] });
        oyente.current?.(evento);
      },
      () => undefined,
    );
    conexion.iniciar();
    return () => conexion.detener();
  }, [entorno, sesion, cliente]);
}
