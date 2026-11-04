import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { useEntorno } from '../../entornoContexto';
import { Celda, Esqueleto, FallaDeCarga, NoEncontrado, Paginacion } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { ErrorApi } from '../../api/resultado';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { mensajeDeErrorApi } from '../../reservas/errores';
import { useAuditoriaConvenio, useConvenio, useEditarConvenio, useRotarPassword, type ConvenioDetalle } from '../api';
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

type Confirmando = 'rotar' | 'estado' | null;

function Ficha({ convenio }: { convenio: ConvenioDetalle }) {
  const { origen } = useEntorno();
  const ubicacion = useLocation();
  const navegar = useNavigate();
  const editar = useEditarConvenio(convenio.id);
  const rotar = useRotarPassword(convenio.id);
  // Recién creado: la contraseña llega una vez por el estado de la navegación y se borra del historial.
  const [password, setPassword] = useState<string | null>((ubicacion.state as { password?: string } | null)?.password ?? null);
  const [confirmando, setConfirmando] = useState<Confirmando>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [linkCopiado, setLinkCopiado] = useState<boolean | null>(null);
  const [editando, setEditando] = useState(false);

  useEffect(() => {
    if ((ubicacion.state as { password?: string } | null)?.password) {
      navegar(ubicacion.pathname, { replace: true, state: null });
    }
  }, [ubicacion.state, ubicacion.pathname, navegar]);

  const link = `${origen}/convenio/${convenio.token_link}`;
  const ocupado = editar.isPending || rotar.isPending;

  async function copiarLink() {
    try {
      await navigator.clipboard.writeText(link);
      setLinkCopiado(true);
    } catch {
      setLinkCopiado(false);
    }
  }

  async function confirmar() {
    setFalla(null);
    setAviso(null);
    try {
      if (confirmando === 'rotar') {
        const { password: nueva } = await rotar.mutateAsync();
        setPassword(nueva);
      } else {
        await editar.mutateAsync({ activo: !convenio.activo });
        setAviso(convenio.activo ? 'Convenio desactivado: su link dejó de funcionar.' : 'Convenio activado: su link vuelve a funcionar.');
      }
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    } finally {
      setConfirmando(null);
    }
  }

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>
          {convenio.cliente_nombre} <span className={estilos.secundario}>{convenio.activo ? 'Activo' : 'Inactivo'}</span>
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
            <div>
              <dt>RUT</dt>
              <dd>{convenio.cliente_rut}</dd>
            </div>
            <div>
              <dt>Reservas</dt>
              <dd>{numero.format(convenio.reservas)}</dd>
            </div>
          </dl>
          <div className={estilos.acciones}>
            <button type="button" className={estilos.botonSecundario} onClick={() => setEditando(true)}>
              Editar
            </button>
          </div>
        </div>
      )}

      <div className={estilos.tarjeta}>
        <h2>Link de reserva</h2>
        {convenio.activo ? (
          <p className={estilos.explicacion}>Trátalo como una credencial: entrégalo solo al cliente. Para entrar también necesita la contraseña.</p>
        ) : (
          <Aviso tipo="error">El convenio está inactivo: este link no funciona (RN-08).</Aviso>
        )}
        <p className={estilos.password} aria-label="Link del convenio">
          {link}
        </p>
        {linkCopiado === true && <Aviso>Link copiado.</Aviso>}
        {linkCopiado === false && <Aviso tipo="error">No se pudo copiar: selecciónalo y cópialo a mano.</Aviso>}
        <div className={estilos.acciones}>
          <button type="button" className={estilos.botonSecundario} onClick={() => void copiarLink()}>
            Copiar link
          </button>
        </div>
      </div>

      <div className={estilos.tarjeta}>
        <h2>Acceso</h2>
        {confirmando ? (
          <>
            <p>
              {confirmando === 'rotar'
                ? 'Se generará una contraseña nueva y la actual dejará de servir. ¿Continuar?'
                : convenio.activo
                  ? 'El link dejará de funcionar. Las reservas ya hechas no se borran ni se cancelan. ¿Continuar?'
                  : 'El link volverá a funcionar con la contraseña vigente. ¿Continuar?'}
            </p>
            <div className={estilos.acciones}>
              <button type="button" className={estilos.boton} disabled={ocupado} onClick={() => void confirmar()}>
                {confirmando === 'rotar' ? 'Rotar' : convenio.activo ? 'Desactivar' : 'Activar'}
              </button>
              <button type="button" className={estilos.botonSecundario} disabled={ocupado} onClick={() => setConfirmando(null)}>
                Cancelar
              </button>
            </div>
          </>
        ) : (
          <div className={estilos.acciones}>
            <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('rotar')}>
              Rotar contraseña
            </button>
            <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando('estado')}>
              {convenio.activo ? 'Desactivar convenio' : 'Activar convenio'}
            </button>
          </div>
        )}
      </div>

      <Auditoria id={convenio.id} />

      {password && <DialogoPassword password={password} cliente={convenio.cliente_nombre} alCerrar={() => setPassword(null)} />}
    </section>
  );
}
