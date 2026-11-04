import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { codigoDe, ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { FallaDeCarga, NoEncontrado } from '../../flota/componentes/comunes';
import { Campo } from '../../formularios/Campo';
import { formatearFechaHora } from '../../hora/hora';
import { mensajeDeErrorApi } from '../../reservas/errores';
import { ESTADOS } from '../../reservas/etiquetas';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { useConversacion, useResponder, type ConversacionDetalle, type Mensaje } from '../api';
import propios from '../conversaciones.module.css';

const VOLVER = '/conversaciones';
const MAXIMO = 1024;
const FUERA_DE_VENTANA = 'Fuera de la ventana de 24 h: solo plantillas aprobadas (pendiente PR-11)';

const ENTREGA: Record<Mensaje['estado_entrega'], string> = {
  QUEUED: 'Enviando',
  SENT: 'Enviado',
  DELIVERED: 'Entregado',
  READ: 'Leído',
  FAILED: 'No se pudo enviar',
};

export function Conversacion() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontrado que="esa conversación" volverA={VOLVER} texto="Volver a las conversaciones" />;
  return <ConversacionDe id={id} />;
}

function ConversacionDe({ id }: { id: number }) {
  const consulta = useConversacion(id);
  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) {
    if (consulta.error instanceof ErrorApi && consulta.error.estado === 404) {
      return <NoEncontrado que="esa conversación" volverA={VOLVER} texto="Volver a las conversaciones" />;
    }
    return <FallaDeCarga error={consulta.error} que="la conversación" reintentar={() => void consulta.refetch()} />;
  }
  return <Hilo conversacion={consulta.data} />;
}

function Hilo({ conversacion }: { conversacion: ConversacionDetalle }) {
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>{conversacion.nombre}</h1>
        <Link to={VOLVER} className={estilos.botonSecundario}>
          Volver a las conversaciones
        </Link>
      </div>
      <div className={estilos.tarjeta}>
        <dl className={estilos.datos}>
          <div>
            <dt>WhatsApp</dt>
            <dd>{conversacion.telefono}</dd>
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
      <Respuesta conversacion={conversacion} />
    </section>
  );
}

function Respuesta({ conversacion }: { conversacion: ConversacionDetalle }) {
  const responder = useResponder(conversacion.id);
  const [texto, setTexto] = useState('');
  const [falla, setFalla] = useState<string | null>(null);
  const [cerrada, setCerrada] = useState(false);
  const fuera = !conversacion.dentro_ventana || cerrada;

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const limpio = texto.trim();
    if (!limpio || fuera) return;
    setFalla(null);
    try {
      await responder.mutateAsync(limpio);
      setTexto('');
    } catch (error) {
      // La ventana pudo cerrarse mientras se escribía: se conserva el texto.
      if (codigoDe(error) === 'fuera_de_ventana') setCerrada(true);
      else setFalla(mensajeDeErrorApi(error));
    }
  }

  return (
    <form className={estilos.tarjeta} onSubmit={(evento) => void enviar(evento)} noValidate>
      {fuera ? (
        <Aviso>{FUERA_DE_VENTANA}</Aviso>
      ) : (
        conversacion.ventana_hasta && <p className={estilos.explicacion}>Puedes responder con texto libre hasta el {formatearFechaHora(conversacion.ventana_hasta)}.</p>
      )}
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <Campo etiqueta="Respuesta">
        {(control) => <textarea rows={3} maxLength={MAXIMO} disabled={fuera} value={texto} onChange={(e) => setTexto(e.target.value)} {...control} />}
      </Campo>
      <div className={estilos.acciones}>
        <button type="submit" className={estilos.boton} disabled={fuera || responder.isPending || !texto.trim()}>
          {responder.isPending ? 'Enviando…' : 'Enviar'}
        </button>
      </div>
    </form>
  );
}
