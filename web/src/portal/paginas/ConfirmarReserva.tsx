import { useMutation } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useParams } from 'react-router';
import { ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import e from '../../diseno/diseno.module.css';
import { formatearFechaHora } from '../../hora/hora';
import { useContextoPortal } from '../contexto';

const MENSAJES: Record<number, { titulo: string; texto: string }> = {
  409: { titulo: 'Esta reserva ya no está pendiente', texto: 'El enlace ya se usó o la reserva cambió. Si tienes dudas, contacta a la central.' },
  410: { titulo: 'El plazo para confirmar venció', texto: 'Tu reserva sigue registrada: la central te contactará para confirmarla.' },
  400: { titulo: 'El enlace no es válido', texto: 'Revisa que lo copiaste completo desde el correo.' },
};

/**
 * HU-51 (CC-22): el enlace del correo. Confirma con un POST (no al cargar el correo: los revisores de enlaces no
 * deben confirmar solos) y muestra «Reserva confirmada».
 */
export function ConfirmarReserva() {
  const { api, slug } = useContextoPortal();
  const { token = '' } = useParams();
  const confirmar = useMutation({
    mutationFn: () => resultado(api.POST('/api/portal/{slug}/reservas/confirmar/', { params: { path: { slug } }, body: { token } })),
  });
  const { mutate } = confirmar;
  // El enlace es de un solo uso: se envía una vez aunque el efecto corra dos veces (StrictMode en desarrollo).
  const enviado = useRef(false);

  useEffect(() => {
    document.title = 'Confirmar reserva';
    if (enviado.current) return;
    enviado.current = true;
    mutate();
  }, [mutate]);

  if (confirmar.isPending || confirmar.isIdle) return <Cargando />;
  if (confirmar.isError) {
    const estado = confirmar.error instanceof ErrorApi ? confirmar.error.estado : 0;
    const mensaje = MENSAJES[estado] ?? { titulo: 'No pudimos confirmar tu reserva', texto: 'Intenta de nuevo en un momento.' };
    return (
      <section className={e.paginaAngosta}>
        <h1 className={e.tituloPagina}>{mensaje.titulo}</h1>
        <Aviso tipo={estado === 410 ? 'info' : 'error'}>{mensaje.texto}</Aviso>
      </section>
    );
  }
  const viaje = confirmar.data;
  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-confirmada">
      <h1 id="titulo-confirmada" className={e.tituloPagina}>
        Reserva confirmada
      </h1>
      <p className={e.subtituloPagina}>
        Tu reserva N.º {viaje.id} quedó confirmada. Te avisaremos por correo cuando la central asigne un conductor.
      </p>
      <dl className={e.resumenFilas}>
        <div>
          <dt>Recogida</dt>
          <dd>{formatearFechaHora(viaje.recogida_en)}</dd>
        </div>
        <div>
          <dt>Desde</dt>
          <dd>{viaje.origen_dir}</dd>
        </div>
        <div>
          <dt>Hasta</dt>
          <dd>{viaje.destino_dir}</dd>
        </div>
      </dl>
    </section>
  );
}
