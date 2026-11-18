import { useEffect, useState } from 'react';
import { Link } from 'react-router';
import estilos from '../alertas/alertas.module.css';
import { useChatEnVivo, type EventoChat } from './enVivoContexto';

type Llegada = Extract<EventoChat, { tipo: 'llegada' }>;

/** HU-63: «Conductor X llegó al origen del viaje Y» en todo el panel, hasta que el despacho la cierra. */
export function AlertasLlegada() {
  const { alRecibir } = useChatEnVivo();
  const [llegadas, setLlegadas] = useState<Llegada[]>([]);

  useEffect(
    () =>
      alRecibir((evento) => {
        if (evento.tipo === 'llegada') setLlegadas((actuales) => [evento, ...actuales.filter((l) => l.viaje !== evento.viaje)]);
      }),
    [alRecibir],
  );

  if (llegadas.length === 0) return null;
  return (
    <section className={estilos.alertas} aria-label="Llegadas al origen" role="status" data-tono="info">
      <ul>
        {llegadas.map((llegada) => (
          <li key={llegada.viaje}>
            <span>
              <strong>Llegó al origen</strong> · {llegada.texto} <Link to={`/reservas/${llegada.viaje}`}>Ver reserva #{llegada.viaje}</Link>
            </span>
            <button type="button" aria-label={`Cerrar el aviso de la reserva ${llegada.viaje}`} onClick={() => setLlegadas((a) => a.filter((l) => l.viaje !== llegada.viaje))}>
              Entendido
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
