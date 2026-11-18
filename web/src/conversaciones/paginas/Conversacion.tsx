import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { FallaDeCarga, NoEncontrado } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { ESTADOS } from '../../reservas/etiquetas';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { useConversacion, type ConversacionDetalle, type Mensaje } from '../api';
import propios from '../conversaciones.module.css';

const VOLVER = '/conversaciones';

const ENTREGA: Record<Mensaje['estado_entrega'], string> = {
  QUEUED: 'Enviando',
  SENT: 'Enviado',
  DELIVERED: 'Entregado',
  READ: 'Leído',
  FAILED: 'No se pudo enviar',
};

/** HU-30 con HU-67 (CC-19): el historial de WhatsApp con un pasajero, en solo lectura (el canal se retiró). */
export function Conversacion() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontrado que="ese historial" volverA={VOLVER} texto="Volver al historial" />;
  return <ConversacionDe id={id} />;
}

function ConversacionDe({ id }: { id: number }) {
  const consulta = useConversacion(id);
  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) {
    if (consulta.error instanceof ErrorApi && consulta.error.estado === 404) {
      return <NoEncontrado que="ese historial" volverA={VOLVER} texto="Volver al historial" />;
    }
    return <FallaDeCarga error={consulta.error} que="el historial" reintentar={() => void consulta.refetch()} />;
  }
  return <Hilo conversacion={consulta.data} />;
}

function Hilo({ conversacion }: { conversacion: ConversacionDetalle }) {
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>{conversacion.nombre}</h1>
        <Link to={VOLVER} className={estilos.botonSecundario}>
          Volver al historial
        </Link>
      </div>
      <Aviso>Historial de WhatsApp en solo lectura: el canal se retiró. Para escribir, usa el Chat.</Aviso>
      <div className={estilos.tarjeta}>
        <dl className={estilos.datos}>
          <div>
            <dt>Teléfono</dt>
            <dd>{conversacion.telefono ?? '—'}</dd>
          </div>
          <div>
            <dt>Reserva</dt>
            <dd>
              {conversacion.reserva ? (
                <Link to={`/reservas/${conversacion.reserva.id}`}>
                  #{conversacion.reserva.id} · {ESTADOS[conversacion.reserva.estado]}
                </Link>
              ) : (
                'Sin reserva'
              )}
            </dd>
          </div>
        </dl>
      </div>
      <ol className={propios.hilo} aria-label="Mensajes">
        {conversacion.mensajes.map((mensaje) => (
          <li key={mensaje.id} className={mensaje.direccion === 'ENTRANTE' ? propios.entrante : propios.saliente}>
            <p className={propios.cuerpo}>{mensaje.cuerpo}</p>
            <span className={mensaje.estado_entrega === 'FAILED' ? propios.fallido : propios.detalle}>
              {formatearFechaHora(mensaje.creado_en)}
              {mensaje.usuario && ` · ${mensaje.usuario}`}
              {mensaje.direccion === 'SALIENTE' && ` · ${ENTREGA[mensaje.estado_entrega]}`}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}
