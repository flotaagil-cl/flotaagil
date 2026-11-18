import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router';
import { resultado } from '../api/resultado';
import { HiloSimple } from '../chat/HiloSimple';
import e from '../diseno/diseno.module.css';
import { Tarjeta } from '../diseno/Tarjeta';
import { useApi } from '../sesion/SesionProvider';

/**
 * HU-66 (CP-54): chat del pasajero con su conductor, de ACEPTADO a FINALIZADO; después queda en solo lectura. Si el
 * viaje no tiene chat (por ejemplo, aún sin conductor), no se muestra.
 */
export function ChatConConductor({ viaje }: { viaje: number }) {
  const api = useApi();
  const chat = useQuery({
    queryKey: ['chat', 'viaje', viaje],
    queryFn: () => resultado(api.POST('/api/chat/viajes/{viaje_id}/', { params: { path: { viaje_id: viaje } } })),
    retry: false,
  });
  if (!chat.data) return null;
  return (
    <Tarjeta como="section" aria-labelledby="titulo-chat-conductor">
      <h2 id="titulo-chat-conductor" className={e.conductorNombre}>
        Chat con tu conductor
      </h2>
      <HiloSimple
        id={chat.data.id}
        puedeEscribir={chat.data.puede_escribir}
        etiqueta="Mensaje para tu conductor"
        soloLectura="El viaje terminó: el chat queda en solo lectura."
      />
      <p className={e.nota}>
        ¿Algo más? <Link to={`/soporte?viaje=${viaje}`}>Escribe a soporte sobre este viaje</Link>.
      </p>
    </Tarjeta>
  );
}
