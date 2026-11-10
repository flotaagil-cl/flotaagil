import { useState } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Celda, Esqueleto, FallaDeCarga, NoEncontrado, Paginacion } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { ErrorApi } from '../../api/resultado';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { mensajeDeErrorApi } from '../../reservas/errores';
import {
  useAccionConvenio,
  useAuditoriaConvenio,
  useConvenio,
  useEditarConvenio,
  useRechazarConvenio,
  useRestablecerPassword,
  type ConvenioDetalle,
} from '../api';
import { ESTADOS_CONVENIO } from '../estados';
import { DialogoPassword, FormularioConvenio } from '../componentes';

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
  CAMBIO_CLAVE: 'Cambio de contraseña',
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
    <div className={estilos.tarjeta}>
      <h2>Auditoría</h2>
      {consulta.isPending ? (
        <Esqueleto etiqueta="Cargando la auditoría" columnas={3} />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="la auditoría" reintentar={() => void consulta.refetch()} />
      ) : consulta.data.results.length === 0 ? (
        <p className={estilos.explicacion}>Aún no hay registros.</p>
      ) : (
        <>
          <table className={estilos.tabla} aria-label="Auditoría del convenio" aria-busy={consulta.isPlaceholderData || undefined}>
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
                  <Celda titulo="Fecha">{formatearFechaHora(registro.creado_en)}</Celda>
                  <Celda titulo="Acción">{ACCIONES_AUDITORIA[registro.accion] ?? registro.accion}</Celda>
                  <Celda titulo="Usuario">{registro.usuario ?? 'Sin usuario'}</Celda>
                </tr>
              ))}
            </tbody>
          </table>
          <Paginacion anterior={Boolean(consulta.data.previous)} siguiente={Boolean(consulta.data.next)} pagina={pagina} ir={setPagina} />
        </>
      )}
    </div>
  );
}

type Confirmando = 'aprobar' | 'desactivar' | 'activar' | 'restablecer' | null;

const PREGUNTAS: Record<Exclude<Confirmando, null>, { texto: string; boton: string }> = {
  aprobar: { texto: 'Aprobar el convenio: podrá pedir viajes y se le avisará por correo.', boton: 'Aprobar' },
  desactivar: { texto: 'Desactivar: la cuenta pierde el acceso al instante. Las reservas no se borran (RN-08).', boton: 'Desactivar' },
  activar: { texto: 'Reactivar: la cuenta vuelve a entrar con su contraseña.', boton: 'Activar' },
  restablecer: { texto: 'Se generará una contraseña temporal y se cerrarán sus sesiones.', boton: 'Restablecer' },
};

function Dato({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div>
      <dt>{titulo}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function Ficha({ convenio }: { convenio: ConvenioDetalle }) {
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
  const ocupado = accion.isPending || rechazar.isPending || restablecer.isPending || editar.isPending;

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
      await ejecutar(() => accion.mutateAsync('aprobar'), 'Convenio aprobado. Se avisó al encargado por correo.');
    } else if (confirmando === 'desactivar') {
      await ejecutar(() => accion.mutateAsync('desactivar'), 'Convenio desactivado: su cuenta perdió el acceso.');
    } else if (confirmando === 'activar') {
      await ejecutar(() => accion.mutateAsync('activar'), 'Convenio activado.');
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
      <div className={estilos.encabezado}>
        <h1>
          {convenio.cliente_nombre} <span className={estilos.secundario}>{ESTADOS_CONVENIO[convenio.estado]}</span>
        </h1>
        <Link to={VOLVER} className={estilos.botonSecundario}>
          Volver a los convenios
        </Link>
      </div>
      {aviso && <Aviso>{aviso}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}

      {editando ? (
        <FormularioConvenio
          iniciales={{ cliente_nombre: convenio.cliente_nombre, cliente_rut: convenio.cliente_rut }}
          textoEnviar="Guardar"
          volverA={`/convenios/${convenio.id}`}
          enviar={async (datos) => {
            await editar.mutateAsync(datos);
            setEditando(false);
            setAviso('Cambios guardados.');
          }}
        />
      ) : (
        <div className={estilos.tarjeta}>
          <h2>Datos</h2>
          <dl className={estilos.datos}>
            <Dato titulo="RUT">{convenio.cliente_rut}</Dato>
            <Dato titulo="Dirección">{convenio.direccion || '—'}</Dato>
            <Dato titulo="Encargado">{convenio.encargado_nombre || '—'}</Dato>
            <Dato titulo="Correo">{convenio.encargado_email || 'Sin cuenta'}</Dato>
            <Dato titulo="Teléfono">{convenio.encargado_telefono || '—'}</Dato>
            <Dato titulo="Reservas">{numero.format(convenio.reservas)}</Dato>
            {convenio.revisado_en && (
              <Dato titulo="Revisado">
                {formatearFechaHora(convenio.revisado_en)} · {convenio.revisado_por}
              </Dato>
            )}
            {convenio.motivo_rechazo && <Dato titulo="Motivo del rechazo">{convenio.motivo_rechazo}</Dato>}
          </dl>
          <div className={estilos.acciones}>
            <button type="button" className={estilos.botonSecundario} onClick={() => setEditando(true)}>
              Editar
            </button>
          </div>
        </div>
      )}

      <div className={estilos.tarjeta}>
        <h2>Estado y acceso</h2>
        {convenio.estado === 'EN_REVISION' && <p>La empresa se registró desde el portal y espera tu revisión.</p>}
        {confirmando ? (
          <div role="alertdialog" aria-labelledby="pregunta-convenio">
            <p id="pregunta-convenio">{PREGUNTAS[confirmando].texto}</p>
            <div className={estilos.acciones}>
              <button type="button" className={estilos.boton} disabled={ocupado} onClick={() => void confirmar()}>
                {PREGUNTAS[confirmando].boton}
              </button>
              <button type="button" className={estilos.botonSecundario} disabled={ocupado} onClick={() => setConfirmando(null)}>
                Volver
              </button>
            </div>
          </div>
        ) : rechazando ? (
          <div>
            <label>
              Motivo del rechazo
              <textarea rows={3} maxLength={200} value={motivo} onChange={(e) => setMotivo(e.target.value)} />
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
          <div className={estilos.acciones}>
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
            {convenio.estado === 'APROBADO' && (
              <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('desactivar')}>
                Desactivar convenio
              </button>
            )}
            {convenio.estado === 'INACTIVO' && (
              <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('activar')}>
                Activar convenio
              </button>
            )}
            {convenio.tiene_cuenta && (
              <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('restablecer')}>
                Restablecer contraseña
              </button>
            )}
          </div>
        )}
      </div>

      {password && (
        <DialogoPassword password={password} cliente={convenio.cliente_nombre} alCerrar={() => setPassword(null)} />
      )}

      <Auditoria id={convenio.id} />
    </section>
  );
}
