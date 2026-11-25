import { useMutation } from '@tanstack/react-query';
import { useParams } from 'react-router';
import { ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Boton } from '../../diseno/Boton';
import e from '../../diseno/diseno.module.css';
import { useTitulo } from '../../diseno/titulo';
import { formatearFechaHora } from '../../hora/hora';
import { useContextoPortal } from '../contexto';

type Decision = 'autorizar' | 'rechazar';

const ERRORES: Record<number, string> = {
  409: 'Esta reserva ya no está pendiente: el enlace ya se usó o la reserva cambió.',
  410: 'El plazo para decidir venció. La central contactará al pasajero.',
  400: 'El enlace no es válido. Revisa que lo copiaste completo desde el correo.',
};

/**
 * HU-54 (CC-22): el contacto del convenio decide sobre una reserva hecha con el RUT de su empresa por un correo no
 * autorizado. Elige con un botón (no al abrir el enlace): autorizar la confirma y rechazar la cancela.
 */
export function AutorizarReserva() {
  const { api, empresa, slug } = useContextoPortal();
  const { token = '' } = useParams();
  const decidir = useMutation({
    mutationFn: (decision: Decision) =>
      resultado(api.POST('/api/portal/{slug}/reservas/autorizar/', { params: { path: { slug } }, body: { token, decision } })),
  });

  useTitulo('Autorizar reserva', empresa.razon_social);

  if (decidir.isSuccess) {
    const viaje = decidir.data;
    const autorizada = viaje.estado === 'SOLICITADO';
    return (
      <section className={e.paginaAngosta}>
        <h1 className={e.tituloPagina}>{autorizada ? 'Reserva autorizada' : 'Reserva rechazada'}</h1>
        <p className={e.subtituloPagina}>
          Reserva N.º {viaje.id}: {viaje.origen_dir} → {viaje.destino_dir}, {formatearFechaHora(viaje.recogida_en)}.{' '}
          {autorizada ? 'Queda en el convenio de tu empresa.' : 'Se avisó al solicitante.'}
        </p>
      </section>
    );
  }

  const estado = decidir.error instanceof ErrorApi ? decidir.error.estado : 0;
  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-autorizar">
      <h1 id="titulo-autorizar" className={e.tituloPagina}>
        ¿Autorizas esta reserva?
      </h1>
      <p className={e.subtituloPagina}>Alguien pidió un traslado con el RUT de tu empresa desde un correo que no está autorizado en el convenio. Los detalles están en el correo.</p>
      {decidir.isError && <Aviso tipo="error">{ERRORES[estado] ?? 'No pudimos registrar tu respuesta. Intenta de nuevo.'}</Aviso>}
      <div className={e.formulario}>
        <Boton ancho cargando={decidir.isPending && decidir.variables === 'autorizar'} disabled={decidir.isPending} onClick={() => decidir.mutate('autorizar')}>
          Autorizar
        </Boton>
        <Boton variante="secundario" ancho disabled={decidir.isPending} onClick={() => decidir.mutate('rechazar')}>
          Rechazar
        </Boton>
      </div>
    </section>
  );
}
