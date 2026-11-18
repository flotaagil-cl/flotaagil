import { useState } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { Celda, Esqueleto, FallaDeCarga, Paginacion } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { ESTADOS } from '../../reservas/etiquetas';
import estilos from '../../componentes/panel.module.css';
import { useConversaciones } from '../api';

const TITULO_HISTORIAL = 'Historial WhatsApp (canal retirado)';
const AVISO_RETIRO = 'El canal de WhatsApp se retiró: este historial es de solo lectura. Para escribir, usa el Chat.';

/** HU-30 con HU-67 (CC-19): historial por pasajero, con la reserva vinculada, en solo lectura. */
export function Conversaciones() {
  const [pagina, setPagina] = useState(1);
  const consulta = useConversaciones(pagina);
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>{TITULO_HISTORIAL}</h1>
        <Link to="/chat" className={estilos.botonSecundario}>
          Ir al Chat
        </Link>
      </div>
      <Aviso>{AVISO_RETIRO}</Aviso>
      {consulta.isPending ? (
        <Esqueleto etiqueta="Cargando el historial" columnas={4} />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="el historial" reintentar={() => void consulta.refetch()} />
      ) : consulta.data.results.length === 0 ? (
        <div className={estilos.vacio}>
          <p>No hay mensajes de WhatsApp en el historial.</p>
        </div>
      ) : (
        <>
          <table className={estilos.tabla} aria-label="Historial de WhatsApp" aria-busy={consulta.isPlaceholderData || undefined}>
            <thead>
              <tr>
                <th scope="col">Pasajero</th>
                <th scope="col">Último mensaje</th>
                <th scope="col">Fecha</th>
                <th scope="col">Reserva</th>
              </tr>
            </thead>
            <tbody>
              {consulta.data.results.map((conversacion) => (
                <tr key={conversacion.id}>
                  <Celda titulo="Pasajero">
                    <Link to={`/conversaciones/${conversacion.id}`}>{conversacion.nombre}</Link>
                  </Celda>
                  <Celda titulo="Último mensaje">
                    {conversacion.ultima_direccion === 'SALIENTE' ? 'Central: ' : ''}
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
