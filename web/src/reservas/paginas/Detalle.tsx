import { useState } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import { esDiaFuturo, formatearFechaHora } from '../../hora/hora';
import { ErrorApi } from '../../api/resultado';
import { useConfirmarPorTelefono, useViaje, useViajes, type ViajeDetalle } from '../api';
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
  const recogidaFutura = esDiaFuturo(viaje.recogida_en);
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
            <>
              <button type="button" className={estilos.boton} disabled={recogidaFutura} onClick={() => setAsignando(true)}>
                Asignar conductor…
              </button>
              {recogidaFutura && <span className={estilos.explicacion}>Disponible para asignar el día del viaje</span>}
            </>
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
              {viaje.pasajero.nombre}
              {viaje.pasajero_cargo ? ` (${viaje.pasajero_cargo})` : ''} · <ContactoPasajero telefono={viaje.pasajero.telefono} />
              {viaje.pasajero_correo ? ` · ${viaje.pasajero_correo}` : ''}
            </dd>
          </div>
          {viaje.solicitante_nombre && (
            <div>
              <dt>Solicitado por</dt>
              <dd>
                {viaje.solicitante_nombre} · <ContactoPasajero telefono={viaje.solicitante_telefono} />
                {viaje.contacto_correo ? ` · ${viaje.contacto_correo}` : ''}
              </dd>
            </div>
          )}
          {viaje.acompanantes.length > 0 && (
            <div>
              <dt>Acompañantes</dt>
              <dd>
                <ul className={estilos.listaSimple}>
                  {viaje.acompanantes.map((a, i) => (
                    <li key={i}>
                      {[a.nombre, a.cargo, a.telefono, a.correo].filter(Boolean).join(' · ')}
                    </li>
                  ))}
                </ul>
              </dd>
            </div>
          )}
          {viaje.grupo && <ViajesDelGrupo grupo={viaje.grupo} actual={viaje.id} />}
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

/** CC-23 (DC-76): los viajes de una misma solicitud en vehículos separados, juntos. Cada uno se despacha aparte. */
function ViajesDelGrupo({ grupo, actual }: { grupo: string; actual: number }) {
  const consulta = useViajes({ grupo, ordenar: ['recogida_en'] });
  return (
    <div id="grupo">
      <dt>Misma solicitud</dt>
      <dd>
        {consulta.isPending ? (
          'Cargando…'
        ) : consulta.isError ? (
          'No se pudo cargar.'
        ) : (
          <ul className={estilos.listaSimple}>
            {consulta.data.results.map((otro) => (
              <li key={otro.id}>
                {otro.id === actual ? (
                  <strong>
                    N.º {otro.id} · {otro.pasajero.nombre} (esta)
                  </strong>
                ) : (
                  <Link to={`/reservas/${otro.id}`}>
                    N.º {otro.id} · {otro.pasajero.nombre}
                  </Link>
                )}{' '}
                · {ESTADOS[otro.estado ?? 'SOLICITADO']}
              </li>
            ))}
          </ul>
        )}
      </dd>
    </div>
  );
}
