import { useState } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import { formatearFechaHora } from '../../hora/hora';
import { ErrorApi } from '../../api/resultado';
import { useConfirmarPorTelefono, useViaje, type ViajeDetalle } from '../api';
import { DialogoAsignar } from '../componentes/DialogoAsignar';
import { DialogoCancelar } from '../componentes/DialogoCancelar';
import { DialogoForzar } from '../componentes/DialogoForzar';
import { ContactoPasajero } from '../componentes/ContactoPasajero';
import { EstadoEtiqueta } from '../componentes/EstadoEtiqueta';
import { NoEncontradaReserva } from '../componentes/NoEncontradaReserva';
import { mensajeDeErrorApi } from '../errores';
import { ACTORES, ALERTAS_VUELO, CANALES, CIERRES_FORZADOS, ESTADOS, ORIGENES_CANCELACION, SENTIDOS } from '../etiquetas';
import { TarjetaVuelo } from '../../vuelos/TarjetaVuelo';
import estilos from '../../componentes/panel.module.css';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { LecturaViaje } from '../../chat/LecturaViaje';

/** HU-66: estados en que puede existir el chat entre el conductor y el pasajero. */
const CON_CHAT: string[] = ['ACEPTADO', 'EN_CAMINO', 'EN_ZONA', 'PASAJERO_A_BORDO', 'FINALIZADO', 'CANCELADO'];

function porQueNo(viaje: ViajeDetalle): string {
  if (viaje.estado === 'ASIGNADO') {
    return 'No se puede editar ni cancelar mientras se espera la respuesta del conductor.';
  }
  if (viaje.estado === 'CANCELADO' || viaje.estado === 'FINALIZADO') return 'La reserva está cerrada.';
  if (viaje.cancelable) return 'Ya fue despachada: se puede cancelar, pero no editar.';
  if (viaje.estado === 'PASAJERO_A_BORDO') return 'Con el pasajero a bordo solo se puede forzar el cierre o la anulación, si el conductor no puede hacerlo.';
  return 'Ya no admite cambios desde el panel.';
}

export function Detalle() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontradaReserva />;
  return <DetalleDe id={id} />;
}

function DetalleDe({ id }: { id: number }) {
  const consulta = useViaje(id);
  const [cancelando, setCancelando] = useState(false);
  const [cancelada, setCancelada] = useState(false);
  const [forzando, setForzando] = useState(false);
  const [forzado, setForzado] = useState<string | null>(null);
  const [asignando, setAsignando] = useState(false);
  const [asignadoA, setAsignadoA] = useState<string | null>(null);

  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) {
    if (consulta.error instanceof ErrorApi && consulta.error.estado === 404) return <NoEncontradaReserva />;
    return (
      <div className={estilos.vacio} role="alert">
        <p>{mensajeDeErrorApi(consulta.error)}</p>
        <button type="button" className={estilos.boton} onClick={() => void consulta.refetch()}>
          Reintentar
        </button>
      </div>
    );
  }
  const viaje = consulta.data;
  const historial = [...viaje.historial].sort((a, b) => Date.parse(a.creado_en) - Date.parse(b.creado_en));

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>
          Reserva #{viaje.id} {viaje.estado && <EstadoEtiqueta estado={viaje.estado} sinConfirmar={viaje.sin_confirmar} />}
          {viaje.alerta_vuelo && <span className={estilos.alerta}>{ALERTAS_VUELO[viaje.alerta_vuelo]}</span>}
        </h1>
        <Link to="/reservas" className={estilos.botonSecundario}>
          Volver a las reservas
        </Link>
      </div>

      {cancelada && <Aviso>Reserva cancelada.</Aviso>}
      {forzado && <Aviso>{forzado}</Aviso>}
      {asignadoA && <Aviso>Reserva asignada a {asignadoA}. Esperando que acepte en la app (60 s).</Aviso>}

      {viaje.sin_confirmar && (
        <Aviso tipo="error">
          Sin confirmar: el plazo para confirmar por correo venció
          {viaje.confirmar_hasta ? ` el ${formatearFechaHora(viaje.confirmar_hasta)}` : ''}. Llama al pasajero y confírmala, cancélala o déjala.
        </Aviso>
      )}

      <div className={estilos.tarjeta}>
        <div className={estilos.acciones}>
          {viaje.estado === 'PENDIENTE_CONFIRMACION' && <ConfirmarPorTelefono id={viaje.id} />}
          {viaje.estado === 'SOLICITADO' && (
            <button type="button" className={estilos.boton} onClick={() => setAsignando(true)}>
              Asignar conductor…
            </button>
          )}
          {viaje.editable && (
            <Link to={`/reservas/${viaje.id}/editar`} className={estilos.boton}>
              Editar
            </Link>
          )}
          {viaje.cancelable && (
            <button type="button" className={estilos.botonPeligro} onClick={() => setCancelando(true)}>
              Cancelar reserva…
            </button>
          )}
          {viaje.estado === 'PASAJERO_A_BORDO' && (
            <button type="button" className={estilos.botonPeligro} onClick={() => setForzando(true)}>
              Forzar cierre o anulación…
            </button>
          )}
        </div>
        {!(viaje.editable && viaje.cancelable) && <p className={estilos.explicacion}>{porQueNo(viaje)}</p>}
      </div>

      {/* HU-69: vuelo con la propuesta de recogida integrada (o la salida con su hora en el aeropuerto). */}
      <TarjetaVuelo viaje={viaje} />

      <div className={estilos.tarjeta}>
        <h2>Datos</h2>
        <dl className={estilos.datos}>
          {viaje.cierre_forzado && (
            <div>
              <dt>{CIERRES_FORZADOS[viaje.cierre_forzado.accion] ?? viaje.cierre_forzado.accion}</dt>
              <dd>
                {viaje.cierre_forzado.motivo}
                <span className={estilos.secundario}>
                  {viaje.cierre_forzado.usuario} · {formatearFechaHora(viaje.cierre_forzado.creado_en)}
                </span>
              </dd>
            </div>
          )}
          <div>
            <dt>Recogida</dt>
            <dd>{formatearFechaHora(viaje.recogida_en)}</dd>
          </div>
          <div>
            <dt>Pasajero</dt>
            <dd>
              {viaje.pasajero.nombre} · <ContactoPasajero telefono={viaje.pasajero.telefono} />
            </dd>
          </div>
          <div>
            <dt>Origen</dt>
            <dd>{viaje.origen.direccion}</dd>
          </div>
          <div>
            <dt>Destino</dt>
            <dd>{viaje.destino.direccion}</dd>
          </div>
          <div>
            <dt>Sentido</dt>
            <dd>{viaje.sentido ? SENTIDOS[viaje.sentido] : '—'}</dd>
          </div>
          <div>
            <dt>Canal</dt>
            <dd>
              {CANALES[viaje.canal]}
              {viaje.convenio ? ` · ${viaje.convenio.cliente_nombre}` : ''}
            </dd>
          </div>
          <div>
            <dt>Conductor</dt>
            <dd>
              {viaje.conductor?.nombre ?? 'Sin asignar'}
              {viaje.vehiculo ? ` · ${viaje.vehiculo.patente}` : ''}
            </dd>
          </div>
          {viaje.calificacion !== null && (
            <div>
              <dt>Calificación</dt>
              <dd>{viaje.calificacion} de 5</dd>
            </div>
          )}
          {viaje.estado === 'CANCELADO' && (
            <div>
              <dt>Cancelación</dt>
              <dd>
                {viaje.motivo_cancelacion ?? '—'}
                {viaje.origen_cancelacion ? ` (${ORIGENES_CANCELACION[viaje.origen_cancelacion]})` : ''}
              </dd>
            </div>
          )}
          <div>
            <dt>Ingresada</dt>
            <dd>{formatearFechaHora(viaje.creado_en)}</dd>
          </div>
        </dl>
      </div>

      {CON_CHAT.includes(viaje.estado ?? '') && <LecturaViaje viaje={viaje.id} />}

      <div className={estilos.tarjeta}>
        <h2 id="titulo-historial">Historial de estados</h2>
        <ol className={estilos.historial} aria-labelledby="titulo-historial">
          {historial.map((cambio, indice) => (
            <li key={`${cambio.creado_en}-${indice}`}>
              <strong>
                {cambio.estado_anterior ? `${ESTADOS[cambio.estado_anterior]} → ` : ''}
                {ESTADOS[cambio.estado_nuevo]}
              </strong>
              <span className={estilos.secundario}>
                {formatearFechaHora(cambio.creado_en)} · {ACTORES[cambio.actor]}
                {cambio.usuario ? ` · ${cambio.usuario}` : ''}
              </span>
              {cambio.manual && (
                <span className={estilos.secundario}>
                  Indicado a mano, sin geocerca ·{' '}
                  {cambio.distancia_m === null || cambio.distancia_m === undefined
                    ? 'sin posición GPS desde que salió'
                    : `a ${new Intl.NumberFormat('es-CL').format(cambio.distancia_m)} m del origen`}
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>

      {forzando && (
        <DialogoForzar
          viaje={viaje}
          alCerrar={() => setForzando(false)}
          alTerminar={(texto) => {
            setForzando(false);
            setForzado(texto);
          }}
        />
      )}

      {asignando && (
        <DialogoAsignar
          viaje={viaje}
          alCerrar={() => setAsignando(false)}
          alAsignar={(nombre) => {
            setAsignando(false);
            setAsignadoA(nombre);
          }}
        />
      )}
      {cancelando && (
        <DialogoCancelar
          viaje={viaje}
          alCerrar={() => setCancelando(false)}
          alCancelar={() => {
            setCancelando(false);
            setCancelada(true);
          }}
        />
      )}
    </section>
  );
}

/** CC-22 (HU-52): el despacho llamó al pasajero y confirma la reserva (queda en el historial y la auditoría). */
function ConfirmarPorTelefono({ id }: { id: number }) {
  const confirmar = useConfirmarPorTelefono(id);
  return (
    <button type="button" className={estilos.boton} disabled={confirmar.isPending} onClick={() => confirmar.mutate()}>
      {confirmar.isPending ? 'Confirmando…' : 'Confirmar por teléfono'}
    </button>
  );
}
