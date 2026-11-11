import { useState, type FormEvent } from 'react';
import { ErrorApi } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import estilos from '../componentes/panel.module.css';
import { Celda, Esqueleto, FallaDeCarga } from '../flota/componentes/comunes';
import { DialogoPassword } from '../flota/componentes/CuentaConductor';
import { Campo } from '../formularios/Campo';
import campos from '../formularios/formularios.module.css';
import { mensajeDeErrorApi } from '../reservas/errores';
import { useSesion } from '../sesion/SesionProvider';
import {
  useAccionUsuario,
  useCrearUsuario,
  useEditarUsuario,
  useRestablecerUsuario,
  useUsuarios,
  type RolPanel,
  type UsuarioPanel,
} from './api';

const ROLES: Record<RolPanel, string> = { ADMINISTRADOR: 'Administrador', DESPACHADOR: 'Despachador' };
const ACCESOS: Record<string, string> = {
  SIN_PASSWORD: 'Sin contraseña',
  TEMPORAL: 'Temporal: debe cambiarla',
  TEMPORAL_VENCIDA: 'Temporal vencida',
  ACTIVA: 'Contraseña propia',
};

type Temporal = { password: string; vence: string; correo: string };
type Confirmando = { usuario: UsuarioPanel; accion: 'desactivar' | 'restablecer' } | null;

/**
 * HU-36: administradores y despachadores de la empresa. Los conductores siguen en su pantalla (HU-10); las
 * cuentas de convenio y pasajero no aparecen. Crear y restablecer muestran la temporal una sola vez (DC-14).
 */
export function Usuarios() {
  const { estado } = useSesion();
  const lista = useUsuarios();
  const accion = useAccionUsuario();
  const restablecer = useRestablecerUsuario();
  const [creando, setCreando] = useState(false);
  const [editando, setEditando] = useState<UsuarioPanel | null>(null);
  const [confirmando, setConfirmando] = useState<Confirmando>(null);
  const [temporal, setTemporal] = useState<Temporal | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const yo = estado.fase === 'autenticada' ? estado.usuario.id : null;

  async function confirmar() {
    if (!confirmando) return;
    const { usuario } = confirmando;
    setFalla(null);
    try {
      if (confirmando.accion === 'desactivar') {
        await accion.mutateAsync({ id: usuario.id, accion: 'desactivar' });
        setAviso(`${usuario.nombre} quedó desactivado: sus sesiones se cerraron.`);
      } else {
        const datos = await restablecer.mutateAsync(usuario.id);
        setTemporal({ password: datos.password_temporal, vence: datos.vence_en, correo: usuario.email });
      }
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    } finally {
      setConfirmando(null);
    }
  }

  async function activar(usuario: UsuarioPanel) {
    setFalla(null);
    try {
      await accion.mutateAsync({ id: usuario.id, accion: 'activar' });
      setAviso(`${usuario.nombre} quedó activo.`);
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    }
  }

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Usuarios</h1>
        <button type="button" className={estilos.boton} onClick={() => { setEditando(null); setCreando(true); }}>
          Nuevo usuario
        </button>
      </div>
      <p>Administradores y despachadores de tu empresa. Los conductores se administran en Conductores.</p>
      {aviso && <Aviso>{aviso}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {(creando || editando) && (
        <FormularioUsuario
          usuario={editando}
          esYo={editando?.id === yo}
          alCerrar={() => {
            setCreando(false);
            setEditando(null);
          }}
          alCrear={(t) => setTemporal(t)}
          alGuardar={(m) => setAviso(m)}
        />
      )}
      {confirmando && (
        <div className={estilos.tarjeta} role="alertdialog" aria-labelledby="pregunta-usuario">
          <p id="pregunta-usuario">
            {confirmando.accion === 'desactivar'
              ? `${confirmando.usuario.nombre} no podrá entrar y sus sesiones se cerrarán al instante.`
              : `Se generará una contraseña temporal para ${confirmando.usuario.nombre} y se cerrarán sus sesiones.`}
          </p>
          <div className={estilos.acciones}>
            <button type="button" className={estilos.botonPeligro} disabled={accion.isPending || restablecer.isPending} onClick={() => void confirmar()}>
              {confirmando.accion === 'desactivar' ? 'Desactivar' : 'Restablecer'}
            </button>
            <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando(null)}>
              Volver
            </button>
          </div>
        </div>
      )}
      {lista.isPending ? (
        <Esqueleto etiqueta="Cargando usuarios" columnas={5} />
      ) : lista.isError ? (
        <FallaDeCarga error={lista.error} que="los usuarios" reintentar={() => void lista.refetch()} />
      ) : (
        <table className={estilos.tabla} aria-label="Usuarios del panel">
          <thead>
            <tr>
              <th scope="col">Nombre</th>
              <th scope="col">Correo</th>
              <th scope="col">Rol</th>
              <th scope="col">Estado</th>
              <th scope="col">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {lista.data.results.map((u) => (
              <tr key={u.id}>
                <Celda titulo="Nombre">
                  {u.nombre}
                  {u.id === yo && ' (tú)'}
                </Celda>
                <Celda titulo="Correo">{u.email}</Celda>
                <Celda titulo="Rol">{ROLES[u.rol as RolPanel]}</Celda>
                <Celda titulo="Estado">{u.activo ? ACCESOS[u.acceso] ?? u.acceso : 'Desactivado'}</Celda>
                <Celda titulo="Acciones">
                  <div className={estilos.acciones}>
                    <button type="button" className={estilos.botonSecundario} onClick={() => { setCreando(false); setEditando(u); }}>
                      Editar
                    </button>
                    {u.activo ? (
                      u.id !== yo && (
                        <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando({ usuario: u, accion: 'desactivar' })}>
                          Desactivar
                        </button>
                      )
                    ) : (
                      <button type="button" className={estilos.botonSecundario} onClick={() => void activar(u)}>
                        Activar
                      </button>
                    )}
                    <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando({ usuario: u, accion: 'restablecer' })}>
                      Restablecer contraseña
                    </button>
                  </div>
                </Celda>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {temporal && <DialogoPassword {...temporal} quien="a esa persona" alCerrar={() => setTemporal(null)} />}
    </section>
  );
}

function FormularioUsuario({
  usuario,
  esYo,
  alCerrar,
  alCrear,
  alGuardar,
}: {
  usuario: UsuarioPanel | null;
  esYo: boolean;
  alCerrar: () => void;
  alCrear: (t: Temporal) => void;
  alGuardar: (mensaje: string) => void;
}) {
  const crear = useCrearUsuario();
  const editar = useEditarUsuario();
  const [nombre, setNombre] = useState(usuario?.nombre ?? '');
  const [email, setEmail] = useState(usuario?.email ?? '');
  const [rol, setRol] = useState<RolPanel>((usuario?.rol as RolPanel) ?? 'DESPACHADOR');
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [falla, setFalla] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const e: Record<string, string> = {};
    if (!nombre.trim()) e.nombre = 'Ingresa el nombre.';
    if (!usuario && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) e.email = 'Ingresa un correo válido.';
    setErrores(e);
    setFalla(null);
    if (Object.keys(e).length) return;
    try {
      if (usuario) {
        await editar.mutateAsync({ id: usuario.id, nombre: nombre.trim(), ...(rol !== usuario.rol && { rol }) });
        alGuardar('Cambios guardados.');
      } else {
        const creado = await crear.mutateAsync({ nombre: nombre.trim(), email: email.trim(), rol });
        alCrear({ password: creado.password_temporal, vence: creado.vence_en, correo: creado.email });
      }
      alCerrar();
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const cuerpo = (error.cuerpo ?? {}) as Record<string, string[] | undefined>;
        setErrores({ ...(cuerpo.email?.[0] && { email: cuerpo.email[0] }), ...(cuerpo.nombre?.[0] && { nombre: cuerpo.nombre[0] }) });
      } else {
        setFalla(mensajeDeErrorApi(error));
      }
    }
  }

  return (
    <form className={estilos.tarjeta} onSubmit={(e) => void enviar(e)} noValidate aria-label={usuario ? 'Editar usuario' : 'Nuevo usuario'}>
      <h2>{usuario ? `Editar a ${usuario.nombre}` : 'Nuevo usuario'}</h2>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <Campo etiqueta="Nombre" error={errores.nombre}>
        {(control) => <input {...control} maxLength={80} value={nombre} onChange={(e) => setNombre(e.target.value)} />}
      </Campo>
      {!usuario && (
        <Campo etiqueta="Correo" error={errores.email}>
          {(control) => <input {...control} type="email" maxLength={120} value={email} onChange={(e) => setEmail(e.target.value)} />}
        </Campo>
      )}
      <label className={campos.campo}>
        Rol
        <select value={rol} disabled={esYo} onChange={(e) => setRol(e.target.value as RolPanel)}>
          <option value="DESPACHADOR">Despachador</option>
          <option value="ADMINISTRADOR">Administrador</option>
        </select>
      </label>
      {esYo && <p className={estilos.secundario}>No puedes cambiar tu propio rol.</p>}
      <div className={estilos.acciones}>
        <button type="submit" className={estilos.boton} disabled={crear.isPending || editar.isPending}>
          {usuario ? 'Guardar' : 'Crear usuario'}
        </button>
        <button type="button" className={estilos.botonSecundario} onClick={alCerrar}>
          Volver
        </button>
      </div>
    </form>
  );
}
