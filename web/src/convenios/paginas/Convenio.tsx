import { useSesion } from '../../sesion/SesionProvider';
import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { Esqueleto, FallaDeCarga, NoEncontrado, Paginacion } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { ErrorApi } from '../../api/resultado';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { mensajeDeErrorApi } from '../../reservas/errores';
import {
  useAccionConvenio,
  useAprobarConvenio,
  useAuditoriaConvenio,
  useConvenio,
  useEditarConvenio,
  useRechazarConvenio,
  useRestablecerPassword,
  type ConvenioDetalle,
} from '../api';
import { BadgeEstado, DialogoPassword, FormularioConvenio } from '../componentes';
import s from '../convenios.module.css';

const VOLVER = '/convenios';
const numero = new Intl.NumberFormat('es-CL');

export function Convenio() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontrado que="convenio" volverA={VOLVER} texto="Volver a los convenios" />;
  return <ConvenioDe id={id} />;
}

function ConvenioDe({ id }: { id: number }) {
  const consulta = useConvenio(id);
  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) {
    if (consulta.error instanceof ErrorApi && consulta.error.estado === 404) {
      return <NoEncontrado que="convenio" volverA={VOLVER} texto="Volver a los convenios" />;
    }
    return <FallaDeCarga error={consulta.error} que="el convenio" reintentar={() => void consulta.refetch()} />;
  }
  return <Ficha convenio={consulta.data} />;
}

const ACCIONES_AUDITORIA: Record<string, string> = {
  CREACION: 'Creación',
  EDICION: 'Edición de datos',
  ACTIVACION: 'Activación',
  DESACTIVACION: 'Desactivación',
  CAMBIO_CLAVE: 'Cambio de contraseña o clave',
  REVOCACION_CLAVE: 'Revocación de la clave del convenio',
  BLOQUEO_CLAVE: 'Bloqueo de la clave por intentos fallidos',
  SOLICITUD_PUBLICA: 'Solicitud desde el portal',
  BLOQUEO_LINK: 'Bloqueo del link por intentos fallidos',
  DESBLOQUEO_LINK: 'Desbloqueo del link al rotar la contraseña',
  REGISTRO: 'Registro desde el portal',
  APROBACION: 'Aprobación',
  RECHAZO: 'Rechazo',
};

/** HU-12: solo lectura, del más nuevo al más antiguo (RN-12). */
function Auditoria({ id }: { id: number }) {
  const [pagina, setPagina] = useState(1);
  const consulta = useAuditoriaConvenio(id, pagina);
  return (
    <div className={s.tarjeta}>
      <div className={s.cabeceraTarjeta}>
        <h2>Auditoría</h2>
      </div>
      {consulta.isPending ? (
        <Esqueleto etiqueta="Cargando la auditoría" columnas={3} />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="la auditoría" reintentar={() => void consulta.refetch()} />
      ) : consulta.data.results.length === 0 ? (
        <p className={estilos.explicacion}>Aún no hay registros.</p>
      ) : (
        <>
          <div className={s.contenedorTabla}>
            <table className={s.tablaConvenios} aria-label="Auditoría del convenio" aria-busy={consulta.isPlaceholderData || undefined}>
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Acción</th>
                  <th scope="col">Usuario</th>
                </tr>
              </thead>
              <tbody>
                {consulta.data.results.map((registro) => (
                  <tr key={registro.id}>
                    <td data-titulo="Fecha" className={s.fechaAuditoria}>
                      <div>{formatearFechaHora(registro.creado_en)}</div>
                    </td>
                    <td data-titulo="Acción">
                      <div>
                        <span className={s.badgeAuditoria}>{ACCIONES_AUDITORIA[registro.accion] ?? registro.accion}</span>
                      </div>
                    </td>
                    <td data-titulo="Usuario">
                      <div>{registro.usuario ?? 'Sin usuario'}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Paginacion anterior={Boolean(consulta.data.previous)} siguiente={Boolean(consulta.data.next)} pagina={pagina} ir={setPagina} />
        </>
      )}
    </div>
  );
}

type Confirmando = 'aprobar' | 'desactivar' | 'activar' | 'restablecer' | 'clave' | 'revocar' | null;

const PREGUNTAS: Record<Exclude<Confirmando, null>, { texto: string; boton: string }> = {
  aprobar: { texto: 'Aprobar el convenio: podrá pedir viajes y se le avisará por correo.', boton: 'Aprobar' },
  desactivar: { texto: 'Desactivar: la cuenta o la clave pierden el acceso al instante. Las reservas no se borran (RN-08).', boton: 'Desactivar' },
  activar: { texto: 'Reactivar el convenio.', boton: 'Activar' },
  clave: {
    texto: 'Se generará una clave nueva y se enviará al correo de contacto. La anterior deja de servir al instante.',
    boton: 'Generar clave',
  },
  revocar: { texto: 'Revocar la clave: nadie podrá pedir con el convenio en el portal hasta generar otra.', boton: 'Revocar' },
  restablecer: { texto: 'Se generará una contraseña temporal y se cerrarán sus sesiones.', boton: 'Restablecer' },
};

function Dato({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <div className={s.datoItem}>
      <dt>{titulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

/** «a@b.cl, @c.cl» o uno por línea → lista sin vacíos. */
function leerCorreos(texto: string): string[] {
  return texto
    .split(/[\s,;]+/)
    .map((c) => c.trim())
    .filter(Boolean);
}

function tipoAcceso(convenio: ConvenioDetalle): string {
  if (convenio.tiene_cuenta) return 'Cuenta web';
  if (convenio.contacto_correo) return 'Solicitud por correo';
  return 'Solo historial';
}

function Ficha({ convenio }: { convenio: ConvenioDetalle }) {
  const { estado: sesion } = useSesion();
  // DC-55 (CC-22): el despachador revisa (aprueba o rechaza); editar, desactivar y la auditoría son del administrador.
  const esAdmin = sesion.fase === 'autenticada' && sesion.usuario.rol === 'ADMINISTRADOR';
  const aprobar = useAprobarConvenio(convenio.id);
  const [correos, setCorreos] = useState(convenio.correos_autorizados.join('\n'));
  const editar = useEditarConvenio(convenio.id);
  const accion = useAccionConvenio(convenio.id);
  const rechazar = useRechazarConvenio(convenio.id);
  const restablecer = useRestablecerPassword(convenio.id);
  const [confirmando, setConfirmando] = useState<Confirmando>(null);
  const [rechazando, setRechazando] = useState(false);
  const [motivo, setMotivo] = useState('');
  const [password, setPassword] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [editando, setEditando] = useState(false);
  const ocupado = accion.isPending || aprobar.isPending || rechazar.isPending || restablecer.isPending || editar.isPending;

  async function ejecutar(fn: () => Promise<unknown>, exito: string) {
    setFalla(null);
    setAviso(null);
    try {
      await fn();
      setAviso(exito);
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    } finally {
      setConfirmando(null);
    }
  }

  async function confirmar() {
    if (confirmando === 'restablecer') {
      await ejecutar(async () => setPassword((await restablecer.mutateAsync()).password_temporal), 'Contraseña restablecida.');
    } else if (confirmando === 'aprobar') {
      await ejecutar(() => aprobar.mutateAsync(leerCorreos(correos)), 'Convenio aprobado. Se avisó a la empresa por correo.');
    } else if (confirmando === 'desactivar') {
      await ejecutar(() => accion.mutateAsync('desactivar'), 'Convenio desactivado: su cuenta perdió el acceso.');
    } else if (confirmando === 'activar') {
      await ejecutar(
        () => accion.mutateAsync('activar'),
        convenio.admite_clave ? 'Convenio activado. Genera una clave nueva para que pueda pedir en el portal.' : 'Convenio activado.',
      );
    } else if (confirmando === 'clave') {
      await ejecutar(() => accion.mutateAsync('regenerar-clave'), 'Clave generada. Se envió al correo de contacto.');
    } else if (confirmando === 'revocar') {
      await ejecutar(() => accion.mutateAsync('revocar-clave'), 'Clave revocada.');
    }
  }

  async function enviarRechazo() {
    if (!motivo.trim()) {
      setFalla('Indica el motivo del rechazo.');
      return;
    }
    await ejecutar(() => rechazar.mutateAsync(motivo.trim()), 'Convenio rechazado. Se avisó al encargado por correo.');
    setRechazando(false);
  }

  return (
    <section>
      <div className={s.encabezado}>
        <div className={s.tituloBloque}>
          <h1>{convenio.cliente_nombre}</h1>
          <div className={s.metaFicha}>
            <BadgeEstado estado={convenio.estado} />
            <span className={s.badgeAcceso} data-cuenta={String(convenio.tiene_cuenta)}>
              {tipoAcceso(convenio)}
            </span>
            <span className={s.metaTexto}>Registrado el {formatearFechaHora(convenio.creado_en)}</span>
          </div>
        </div>
        <div className={s.accionesEncabezado}>
          <Link to={VOLVER} className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
            <Icono nombre="atras" tamano={16} />
            Volver a los convenios
          </Link>
        </div>
      </div>

      {aviso && <Aviso>{aviso}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}

      <div className={s.cuadriculaFicha}>
        <div className={s.columnaPrincipal}>
          {editando ? (
            <FormularioConvenio
              iniciales={{ cliente_nombre: convenio.cliente_nombre, cliente_rut: convenio.cliente_rut }}
              textoEnviar="Guardar"
              volverA={`/convenios/${convenio.id}`}
              alCancelar={() => setEditando(false)}
              enviar={async (datos) => {
                await editar.mutateAsync(datos);
                setEditando(false);
                setAviso('Cambios guardados.');
              }}
            />
          ) : (
            <div className={s.tarjeta}>
              <div className={s.cabeceraTarjeta}>
                <h2>Datos</h2>
                {esAdmin && (
                  <button type="button" className={estilos.botonSecundario} onClick={() => setEditando(true)}>
                    Editar
                  </button>
                )}
              </div>
              <dl className={s.datosGrid}>
                <Dato titulo="RUT">
                  <span className={s.rut}>{convenio.cliente_rut}</span>
                </Dato>
                <Dato titulo="Dirección">{convenio.direccion || '—'}</Dato>
                <Dato titulo="Encargado">{convenio.encargado_nombre || '—'}</Dato>
                <Dato titulo="Correo">{convenio.encargado_email || 'Sin cuenta'}</Dato>
                <Dato titulo="Teléfono">{convenio.encargado_telefono || '—'}</Dato>
                {convenio.contacto_correo && <Dato titulo="Correo de contacto">{convenio.contacto_correo}</Dato>}
                {convenio.viajes_estimados_mes != null && <Dato titulo="Viajes al mes (estimado)">{numero.format(convenio.viajes_estimados_mes)}</Dato>}
                <Dato titulo="Correos autorizados">
                  {convenio.correos_autorizados.length ? (
                    <div className={s.listaCorreos}>
                      {convenio.correos_autorizados.map((correo) => (
                        <span key={correo} className={s.chipCorreo}>
                          {correo}
                        </span>
                      ))}
                    </div>
                  ) : (
                    '—'
                  )}
                </Dato>
                <Dato titulo="Reservas">
                  <span className={s.pillReservas}>{numero.format(convenio.reservas)}</span>
                </Dato>
                {convenio.revisado_en && (
                  <Dato titulo="Revisado">
                    {formatearFechaHora(convenio.revisado_en)} · {convenio.revisado_por}
                  </Dato>
                )}
              </dl>
              {convenio.motivo_rechazo && (
                <div className={s.bloqueRechazo}>
                  <strong>Motivo del rechazo</strong>
                  <p>{convenio.motivo_rechazo}</p>
                </div>
              )}
            </div>
          )}

          {esAdmin && <Auditoria id={convenio.id} />}
        </div>

        <aside className={s.columnaLateral}>
          <div className={s.tarjeta}>
            <div className={s.cabeceraTarjeta}>
              <h2>Estado y acceso</h2>
              <BadgeEstado estado={convenio.estado} />
            </div>
            {convenio.estado === 'EN_REVISION' && (
              <p className={s.notaEstado}>La empresa lo solicitó desde el portal y espera tu revisión.</p>
            )}
            {!convenio.tiene_cuenta && (
              <p className={s.notaEstado}>
                {convenio.admite_clave
                  ? 'Sin cuenta (CC-23): el contacto y los correos autorizados piden en el portal con la clave del convenio.'
                  : convenio.contacto_correo
                    ? 'Sin cuenta (CC-22): sus reservas del portal con el RUT y un correo autorizado quedan en el convenio.'
                    : 'Convenio anterior al registro en el portal, sin cuenta: queda como historial.'}
              </p>
            )}
            {convenio.admite_clave && convenio.estado !== 'EN_REVISION' && convenio.estado !== 'RECHAZADO' && (
              <p className={s.notaEstado}>
                {convenio.clave_vigente && convenio.clave_generada_en
                  ? `Clave vigente, generada el ${formatearFechaHora(convenio.clave_generada_en)}. Nunca se muestra aquí.`
                  : 'Sin clave vigente: nadie puede pedir con el convenio en el portal.'}
              </p>
            )}
            {confirmando ? (
              <div className={s.panelConfirmacion} role="alertdialog" aria-labelledby="pregunta-convenio">
                <p id="pregunta-convenio">
                  {confirmando === 'aprobar' && convenio.admite_clave
                    ? 'Aprobar el convenio: se generará su clave y se enviará al correo de contacto con el aviso de aprobación.'
                    : PREGUNTAS[confirmando].texto}
                </p>
                {confirmando === 'aprobar' && (
                  <label className={s.campoTextarea}>
                    Correos autorizados (uno por línea; «@empresa.cl» autoriza todo el dominio)
                    <textarea className={s.textarea} rows={4} value={correos} onChange={(e) => setCorreos(e.target.value)} />
                  </label>
                )}
                <div className={estilos.acciones}>
                  <button type="button" className={estilos.boton} disabled={ocupado} onClick={() => void confirmar()}>
                    {confirmando === 'clave' && convenio.clave_vigente ? 'Regenerar clave' : PREGUNTAS[confirmando].boton}
                  </button>
                  <button type="button" className={estilos.botonSecundario} disabled={ocupado} onClick={() => setConfirmando(null)}>
                    Volver
                  </button>
                </div>
              </div>
            ) : rechazando ? (
              <div className={s.panelRechazo}>
                <label className={s.campoTextarea}>
                  Motivo del rechazo
                  <textarea className={s.textarea} rows={3} maxLength={200} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
                </label>
                <div className={estilos.acciones}>
                  <button type="button" className={estilos.botonPeligro} disabled={ocupado} onClick={() => void enviarRechazo()}>
                    Rechazar
                  </button>
                  <button type="button" className={estilos.botonSecundario} disabled={ocupado} onClick={() => setRechazando(false)}>
                    Volver
                  </button>
                </div>
              </div>
            ) : (
              <div className={s.accionesColumna}>
                {convenio.estado === 'EN_REVISION' && (
                  <>
                    <button type="button" className={estilos.boton} onClick={() => setConfirmando('aprobar')}>
                      Aprobar
                    </button>
                    <button type="button" className={estilos.botonSecundario} onClick={() => setRechazando(true)}>
                      Rechazar…
                    </button>
                  </>
                )}
                {esAdmin && convenio.estado === 'APROBADO' && (
                  <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('desactivar')}>
                    Desactivar convenio
                  </button>
                )}
                {esAdmin && convenio.estado === 'APROBADO' && convenio.admite_clave && (
                  <button type="button" className={`${estilos.botonSecundario} ${s.botonConIcono}`} onClick={() => setConfirmando('clave')}>
                    <Icono nombre="llave" tamano={16} />
                    {convenio.clave_vigente ? 'Regenerar clave' : 'Generar clave'}
                  </button>
                )}
                {esAdmin && convenio.admite_clave && convenio.clave_vigente && (
                  <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('revocar')}>
                    Revocar clave
                  </button>
                )}
                {esAdmin && convenio.estado === 'INACTIVO' && (convenio.tiene_cuenta || convenio.admite_clave) && (
                  <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('activar')}>
                    Activar convenio
                  </button>
                )}
                {esAdmin && convenio.tiene_cuenta && (
                  <button
                    type="button"
                    className={`${estilos.botonSecundario} ${s.botonConIcono}`}
                    onClick={() => setConfirmando('restablecer')}
                  >
                    <Icono nombre="llave" tamano={16} />
                    Restablecer contraseña
                  </button>
                )}
              </div>
            )}
          </div>
        </aside>
      </div>

      {password && (
        <DialogoPassword password={password} cliente={convenio.cliente_nombre} alCerrar={() => setPassword(null)} />
      )}
    </section>
  );
}
