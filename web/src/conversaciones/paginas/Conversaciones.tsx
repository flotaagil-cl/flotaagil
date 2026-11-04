import { useState } from 'react';
import { Link } from 'react-router';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { ESTADOS } from '../../reservas/etiquetas';
import estilos from '../../componentes/panel.module.css';
import { useConversaciones } from '../api';

/** HU-30: bandeja por pasajero, con la reserva vinculada. */
export function Conversaciones() {
  const [pagina, setPagina] = useState(1);
  const consulta = useConversaciones(pagina);
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Conversaciones</h1>
      </div>
      {consulta.isPending ? (
        <Esqueleto etiqueta="Cargando conversaciones" columnas={5} />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="las conversaciones" reintentar={() => void consulta.refetch()} />
      ) : consulta.data.results.length === 0 ? (
        <div className={estilos.vacio}>
          <p>Aún no hay conversaciones de WhatsApp.</p>
        </div>
      ) : (
        <>
          <table className={estilos.tabla} aria-label="Conversaciones" aria-busy={consulta.isPlaceholderData || undefined}>
            <thead>
              <tr>
                <th scope="col">Pasajero</th>
                <th scope="col">Último mensaje</th>
                <th scope="col">Fecha</th>
                <th scope="col">Reserva</th>
                <th scope="col">Ventana de 24 h</th>
              </tr>
            </thead>
            <tbody>
              {consulta.data.results.map((conversacion) => (
                <tr key={conversacion.id}>
                  <Celda titulo="Pasajero">
                    <Link to={`/conversaciones/${conversacion.id}`}>{conversacion.nombre}</Link>
                  </Celda>
                  <Celda titulo="Último mensaje">
                    {conversacion.ultima_direccion === 'SALIENTE' ? 'Tú: ' : ''}
                    {conversacion.ultimo_mensaje}
                  </Celda>
                  <Celda titulo="Fecha">{formatearFechaHora(conversacion.ultimo_en)}</Celda>
                  <Celda titulo="Reserva">
                    {conversacion.reserva ? (
                      <Link to={`/reservas/${conversacion.reserva.id}`}>
                        #{conversacion.reserva.id} · {ESTADOS[conversacion.reserva.estado]}
                      </Link>
                    ) : (
                      'Sin reserva'
                    )}
                  </Celda>
                  <Celda titulo="Ventana de 24 h">{conversacion.dentro_ventana ? 'Abierta' : 'Cerrada'}</Celda>
                </tr>
              ))}
            </tbody>
          </table>
          <Paginacion anterior={Boolean(consulta.data.previous)} siguiente={Boolean(consulta.data.next)} pagina={pagina} ir={setPagina} />
        </>
      )}
    </section>
  );
}
