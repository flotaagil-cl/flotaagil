import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router';
import type { components } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { iniciales } from '../diseno/clases';
import { Dialogo } from '../diseno/Dialogo';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import { MINIMO_PASSWORD, reglasPassword } from '../diseno/password';
import { ReglasPassword } from '../diseno/ReglasPassword';
import { Insignia } from '../diseno/Tarjeta';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { MarcoPasajero } from '../viajes/MarcoPasajero';
import { PALABRA_ELIMINAR, mesYAnio, telefonoLegible } from './perfil';
import p from './perfil.module.css';

type MiCuenta = components['schemas']['MiCuenta'];

/**
 * HU-45: «Mi perfil» del pasajero. Edita su nombre y su WhatsApp (uno nuevo se confirma por WhatsApp y, mientras
 * tanto, se sigue usando el anterior, DC-50); el correo es su usuario y no se cambia aquí. Cambia la contraseña,
 * cierra sesión y elimina la cuenta escribiendo ELIMINAR (Ley 21.719): se anonimizan sus datos y se conservan los
 * viajes, los pagos y la auditoría.
 */
export function MiPerfil() {
  const { estado } = useSesion();
  const api = useApi();
  const perfil = useQuery({ queryKey: ['mi-cuenta', 'perfil'], queryFn: () => resultado(api.GET('/api/mi-cuenta/')) });

  useEffect(() => {
    document.title = 'Mi perfil';
  }, []);

  if (estado.fase !== 'autenticada') return null;
  if (estado.usuario.rol !== 'PASAJERO') return <Navigate to={inicioDeRol(estado.usuario.rol)} replace />;

  return (
    <MarcoPasajero>
      <div className={p.pagina}>
        {perfil.isPending && <Cargando />}
        {perfil.isError && <Aviso tipo="error">No pudimos cargar tu perfil. Recarga la página.</Aviso>}
        {perfil.data && (
          <>
            <Resumen cuenta={perfil.data} />
            <div className={p.columna}>
              <h1 className={e.tituloPagina}>Mi perfil</h1>
              <DatosPersonales key={`${perfil.data.nombre}|${perfil.data.telefono}`} cuenta={perfil.data} />
              <SeguridadYCuenta cuenta={perfil.data} />
            </div>
          </>
        )}
      </div>
    </MarcoPasajero>
  );
}

function Resumen({ cuenta }: { cuenta: MiCuenta }) {
  const desde = mesYAnio(cuenta.pasajero_desde);
  return (
    <section className={`${e.tarjeta} ${p.resumen}`} aria-label="Tu cuenta">
      <span className={p.avatarGrande} aria-hidden="true">
        {iniciales(cuenta.nombre)}
      </span>
      <div className={p.resumenTexto}>
        <p className={p.nombre}>{cuenta.nombre}</p>
        {desde && <p className={p.desde}>Pasajero desde {desde}</p>}
        <Insignia tono="ok">Cuenta verificada</Insignia>
      </div>
    </section>
  );
}

function DatosPersonales({ cuenta }: { cuenta: MiCuenta }) {
  const api = useApi();
  const { sesion } = useSesion();
  const consultas = useQueryClient();
  const [nombre, setNombre] = useState(cuenta.nombre);
  const [telefono, setTelefono] = useState(cuenta.telefono_pendiente ?? cuenta.telefono);
  const [errores, setErrores] = useState<{ nombre?: string; telefono?: string }>({});
  const [falla, setFalla] = useState<string | null>(null);
  const [guardado, setGuardado] = useState(false);

  const guardar = useMutation({
    mutationFn: () => resultado(api.PATCH('/api/mi-cuenta/', { body: { nombre: nombre.trim(), telefono: telefono.trim() } })),
    onSuccess: (datos) => {
      sesion.actualizarUsuario({ nombre: datos.nombre });
      consultas.setQueryData(['mi-cuenta', 'perfil'], datos);
      setGuardado(true);
    },
    onError: (error) => {
      const cuerpo = error instanceof ErrorApi ? ((error.cuerpo ?? {}) as Record<string, unknown>) : {};
      const primero = (campo: string) => (Array.isArray(cuerpo[campo]) ? String((cuerpo[campo] as string[])[0]) : undefined);
      if (primero('nombre') || primero('telefono')) {
        setErrores({ nombre: primero('nombre'), telefono: primero('telefono') });
      } else if (error instanceof ErrorApi && error.estado === 409) {
        setErrores({ telefono: 'Ese WhatsApp ya está asociado a otra cuenta de esta empresa.' });
      } else if (error instanceof ErrorApi && error.estado === 429) {
        setFalla('Ya te enviamos varios mensajes. Espera unos minutos e intenta de nuevo.');
      } else {
        setFalla('No se pudieron guardar los cambios. Intenta de nuevo.');
      }
    },
  });

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    setGuardado(false);
    setFalla(null);
    const encontrados: { nombre?: string; telefono?: string } = {};
    if (!nombre.trim()) encontrados.nombre = 'Escribe tu nombre y apellido.';
    if (!telefono.trim()) encontrados.telefono = 'Escribe tu WhatsApp.';
    setErrores(encontrados);
    if (Object.keys(encontrados).length === 0) guardar.mutate();
  }

  return (
    <section className={e.tarjeta} aria-labelledby="datos-personales">
      <h2 id="datos-personales" className={p.tituloSeccion}>
        Datos personales
      </h2>
      <form className={e.formulario} onSubmit={enviar} noValidate aria-label="Datos personales">
        <Campo etiqueta="Nombre y apellido" autoComplete="name" maxLength={80} value={nombre} error={errores.nombre} onChange={(ev) => setNombre(ev.target.value)} />
        <Campo etiqueta="Correo" type="email" value={cuenta.email} readOnly ayuda="Para cambiar tu correo, contacta a la empresa." />
        <Campo
          etiqueta="WhatsApp"
          type="tel"
          inputMode="tel"
          autoComplete="tel"
          value={telefono}
          error={errores.telefono}
          ayuda="Si cambias tu WhatsApp, te pediremos confirmarlo de nuevo."
          onChange={(ev) => setTelefono(ev.target.value)}
        />
        {cuenta.telefono_pendiente && (
          <Aviso>
            Te enviamos un WhatsApp al {telefonoLegible(cuenta.telefono_pendiente)}. Responde CONFIRMAR CUENTA para usarlo; mientras tanto te
            seguimos escribiendo al {telefonoLegible(cuenta.telefono)}.
          </Aviso>
        )}
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        {guardado && !cuenta.telefono_pendiente && <Aviso>Cambios guardados.</Aviso>}
        <div>
          <Boton type="submit" cargando={guardar.isPending}>
            {guardar.isPending ? 'Guardando…' : 'Guardar cambios'}
          </Boton>
        </div>
      </form>
    </section>
  );
}

function SeguridadYCuenta({ cuenta }: { cuenta: MiCuenta }) {
  const { estado, sesion } = useSesion();
  const navegar = useNavigate();
  const [dialogo, setDialogo] = useState<'password' | 'eliminar' | null>(null);
  if (estado.fase !== 'autenticada') return null;
  const ingreso = `/solicitar/${cuenta.empresa_slug}/ingresar`;
  const salir = () => void sesion.logout().then(() => navegar(ingreso, { replace: true }));
  const cambiada = mesYAnio(cuenta.password_cambiada_en);

  return (
    <section className={e.tarjeta} aria-labelledby="seguridad">
      <h2 id="seguridad" className={p.tituloSeccion}>
        Seguridad y cuenta
      </h2>
      <ul className={p.acciones}>
        <li>
          <button type="button" className={p.accion} onClick={() => setDialogo('password')}>
            <Icono nombre="candado" tamano={20} />
            <span className={p.accionTexto}>
              <span className={p.accionTitulo}>Cambiar contraseña</span>
              <span className={p.accionDetalle}>{cambiada ? `Último cambio: ${cambiada}` : 'Nunca la has cambiado'}</span>
            </span>
            <Icono nombre="derecha" tamano={18} />
          </button>
        </li>
        <li>
          <button type="button" className={p.accion} onClick={salir}>
            <Icono nombre="salir" tamano={20} />
            <span className={p.accionTexto}>
              <span className={p.accionTitulo}>Cerrar sesión</span>
            </span>
            <Icono nombre="derecha" tamano={18} />
          </button>
        </li>
        <li>
          <button type="button" className={`${p.accion} ${p.peligro}`} onClick={() => setDialogo('eliminar')}>
            <Icono nombre="basurero" tamano={20} />
            <span className={p.accionTexto}>
              <span className={p.accionTitulo}>Eliminar mi cuenta</span>
              <span className={p.accionDetalle}>Borra tus datos personales de forma permanente</span>
            </span>
            <Icono nombre="derecha" tamano={18} />
          </button>
        </li>
      </ul>
      <CambiarPassword abierto={dialogo === 'password'} email={estado.usuario.email} onCerrar={() => setDialogo(null)} />
      <EliminarCuenta abierto={dialogo === 'eliminar'} ingreso={ingreso} onCerrar={() => setDialogo(null)} />
    </section>
  );
}

function CambiarPassword({ abierto, email, onCerrar }: { abierto: boolean; email: string; onCerrar: () => void }) {
  const api = useApi();
  const { sesion } = useSesion();
  const consultas = useQueryClient();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [errores, setErrores] = useState<{ actual?: string; nueva?: string; repetida?: string }>({});
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  function cerrar() {
    setActual('');
    setNueva('');
    setRepetida('');
    setErrores({});
    setFalla(null);
    onCerrar();
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados: typeof errores = {};
    if (!actual) encontrados.actual = 'Escribe tu contraseña actual.';
    if (nueva.length < MINIMO_PASSWORD) encontrados.nueva = `Mínimo ${MINIMO_PASSWORD} caracteres.`;
    else if (nueva === actual) encontrados.nueva = 'Debe ser distinta de la actual.';
    if (repetida !== nueva) encontrados.repetida = 'Las contraseñas no coinciden.';
    setErrores(encontrados);
    setFalla(null);
    if (Object.keys(encontrados).length) return;
    setEnviando(true);
    try {
      await resultado(api.POST('/api/auth/password/', { body: { password_actual: actual, password_nueva: nueva } }));
      // Cambiar la clave cierra las demás sesiones; esta sigue con la clave nueva.
      await sesion.login(email, nueva);
      void consultas.invalidateQueries({ queryKey: ['mi-cuenta', 'perfil'] });
      cerrar();
    } catch (error) {
      const cuerpo = error instanceof ErrorApi ? ((error.cuerpo ?? {}) as Record<string, string[] | undefined>) : {};
      if (cuerpo.password_actual?.[0] || cuerpo.password_nueva?.[0]) {
        setErrores({
          ...(cuerpo.password_actual?.[0] && { actual: cuerpo.password_actual[0] }),
          ...(cuerpo.password_nueva?.[0] && { nueva: cuerpo.password_nueva[0] }),
        });
      } else {
        setFalla('No se pudo cambiar la contraseña. Intenta de nuevo.');
      }
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Dialogo abierto={abierto} titulo="Cambiar contraseña" onCerrar={cerrar}>
      <form className={e.formulario} onSubmit={(ev) => void enviar(ev)} noValidate aria-label="Cambiar contraseña">
        <Campo etiqueta="Contraseña actual" type="password" autoComplete="current-password" value={actual} error={errores.actual} onChange={(ev) => setActual(ev.target.value)} />
        <Campo
          etiqueta="Contraseña nueva"
          type="password"
          autoComplete="new-password"
          value={nueva}
          error={errores.nueva}
          aria-describedby="reglas-mi-perfil"
          onChange={(ev) => setNueva(ev.target.value)}
        />
        <Campo etiqueta="Repite la contraseña nueva" type="password" autoComplete="new-password" value={repetida} error={errores.repetida} onChange={(ev) => setRepetida(ev.target.value)} />
        <ReglasPassword reglas={reglasPassword(nueva, repetida)} id="reglas-mi-perfil" />
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <Boton type="submit" ancho cargando={enviando}>
          {enviando ? 'Guardando…' : 'Cambiar contraseña'}
        </Boton>
      </form>
    </Dialogo>
  );
}

function EliminarCuenta({ abierto, ingreso, onCerrar }: { abierto: boolean; ingreso: string; onCerrar: () => void }) {
  const api = useApi();
  const { sesion } = useSesion();
  const navegar = useNavigate();
  const [palabra, setPalabra] = useState('');
  const [falla, setFalla] = useState<string | null>(null);
  const eliminar = useMutation({
    // 204 sin cuerpo: `resultado` exige datos, así que se mira la respuesta directamente.
    mutationFn: async () => {
      const { response } = await api.DELETE('/api/mi-cuenta/');
      if (!response.ok) throw new ErrorApi(response.status, null);
    },
    onSuccess: () => {
      // La sesión ya quedó revocada en el servidor; aquí solo se limpia.
      void sesion.logout().finally(() => navegar(ingreso, { replace: true }));
    },
    onError: (error) => {
      setFalla(
        error instanceof ErrorApi && error.estado === 409
          ? 'Tienes un viaje en curso. Podrás eliminar tu cuenta cuando termine o lo canceles.'
          : 'No se pudo eliminar tu cuenta. Intenta de nuevo.',
      );
    },
  });

  function cerrar() {
    setPalabra('');
    setFalla(null);
    onCerrar();
  }

  const confirmada = palabra.trim().toUpperCase() === PALABRA_ELIMINAR;
  return (
    <Dialogo abierto={abierto} titulo="¿Eliminar tu cuenta?" onCerrar={cerrar}>
      <div className={e.formulario}>
        <p className={e.saludo}>Esto no se puede deshacer.</p>
        <div className={p.explicacion}>
          <p className={p.explicacionTitulo}>Se borran</p>
          <ul>
            <li>Tu nombre, tu correo y tu WhatsApp.</li>
            <li>Tu contraseña y tus sesiones abiertas.</li>
            <li>El contenido de tus mensajes de WhatsApp con la central.</li>
          </ul>
          <p className={p.explicacionTitulo}>Se conservan, sin tus datos personales</p>
          <ul>
            <li>Tus viajes, sus pagos y su historial, por obligación contable.</li>
            <li>El registro de que eliminaste tu cuenta.</li>
          </ul>
        </div>
        <Campo etiqueta={`Escribe ${PALABRA_ELIMINAR} para confirmar`} autoComplete="off" value={palabra} onChange={(ev) => setPalabra(ev.target.value)} />
        {falla && (
          <p className={e.alerta} role="alert">
            {falla}
          </p>
        )}
        <Boton variante="peligro" ancho disabled={!confirmada} cargando={eliminar.isPending} onClick={() => eliminar.mutate()}>
          {eliminar.isPending ? 'Eliminando…' : 'Eliminar mi cuenta'}
        </Boton>
        <Boton variante="secundario" ancho onClick={cerrar}>
          Volver
        </Boton>
      </div>
    </Dialogo>
  );
}
