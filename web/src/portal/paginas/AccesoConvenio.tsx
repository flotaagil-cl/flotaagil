import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { useParams } from 'react-router';
import { MENSAJES } from '../../api/errores';
import { codigoDe, detalleDe, ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Campo } from '../../formularios/Campo';
import { useEntorno } from '../../entornoContexto';
import {
  crearClientePortal,
  useAccesoConvenio,
  useEntrarConvenio,
  useSalirConvenio,
  useSolicitarConvenio,
  type AccesoConvenio as Acceso,
  type ClientePortal,
  type Solicitud,
} from '../api';
import { Confirmacion } from '../Confirmacion';
import { FormularioSolicitud } from '../FormularioSolicitud';
import estilos from '../portal.module.css';

/** HU-25: el link del convenio pide la contraseña y lleva al formulario, sin la sesión del panel. */
export function AccesoConvenio() {
  const entorno = useEntorno();
  const [{ api, cliente }] = useState(() => ({
    api: crearClientePortal(entorno),
    cliente: new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false }, mutations: { retry: false } } }),
  }));
  return (
    <QueryClientProvider client={cliente}>
      <Marco api={api} />
    </QueryClientProvider>
  );
}

function LinkNoDisponible() {
  return (
    <section className={estilos.tarjeta}>
      <h1>Este link de convenio no está disponible</h1>
      <p>No existe o el convenio ya no está vigente. Habla con la empresa de transporte.</p>
    </section>
  );
}

function Marco({ api }: { api: ClientePortal }) {
  const { token = '' } = useParams();
  const acceso = useAccesoConvenio(api, token);
  const [noDisponible, setNoDisponible] = useState(false);
  const [vencida, setVencida] = useState(false);
  const datos = acceso.data;
  const razonSocial = datos?.razon_social;

  useEffect(() => {
    document.title = razonSocial ? `Solicitud de convenio · ${razonSocial}` : 'Solicitud de convenio';
  }, [razonSocial]);

  let contenido;
  if (noDisponible || (acceso.error instanceof ErrorApi && acceso.error.estado === 404)) {
    contenido = <LinkNoDisponible />;
  } else if (acceso.isPending) {
    contenido = (
      <div className={estilos.esqueleto} role="status" aria-label="Cargando">
        <span />
        <span />
        <span />
      </div>
    );
  } else if (acceso.isError) {
    contenido = (
      <section className={estilos.tarjeta} role="alert">
        <h1>No se pudo conectar con el servidor</h1>
        <p>{MENSAJES.sin_conexion}</p>
        <button type="button" className={estilos.botonPrincipal} onClick={() => void acceso.refetch()}>
          Reintentar
        </button>
      </section>
    );
  } else if (!acceso.data.sesion_activa) {
    contenido = <Contrasena api={api} token={token} vencida={vencida} alNoDisponible={() => setNoDisponible(true)} />;
  } else {
    contenido = (
      <ConSesion
        api={api}
        token={token}
        acceso={acceso.data}
        alNoDisponible={() => setNoDisponible(true)}
        alVencer={() => {
          setVencida(true);
          void acceso.refetch();
        }}
      />
    );
  }

  return (
    <div className={estilos.pagina}>
      <header className={estilos.cabecera}>
        <span className={estilos.marca}>{razonSocial ?? 'Solicitud de convenio'}</span>
        {datos?.cliente_nombre && <span className={estilos.subtitulo}>Convenio {datos.cliente_nombre}</span>}
      </header>
      <main className={estilos.contenido}>{contenido}</main>
      <footer className={estilos.piePagina}>
        <span>Operado con FlotaÁgil</span>
      </footer>
    </div>
  );
}

function Contrasena({ api, token, vencida, alNoDisponible }: { api: ClientePortal; token: string; vencida: boolean; alNoDisponible: () => void }) {
  const entrar = useEntrarConvenio(api, token);
  const [password, setPassword] = useState('');
  const [falla, setFalla] = useState<string | null>(null);
  const [faltante, setFaltante] = useState(false);

  async function enviar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    setFalla(null);
    setFaltante(!password);
    if (!password) return;
    try {
      await entrar.mutateAsync(password);
    } catch (error) {
      setPassword('');
      if (error instanceof ErrorApi && error.estado === 404) alNoDisponible();
      else if (codigoDe(error) === 'credenciales_invalidas') setFalla('La contraseña no es correcta.');
      else if (codigoDe(error) === 'convenio_bloqueado') setFalla('El acceso quedó bloqueado por intentos fallidos. Intenta de nuevo más tarde.');
      else setFalla(error instanceof ErrorApi ? (detalleDe(error) ?? MENSAJES.sin_conexion) : MENSAJES.sin_conexion);
    }
  }

  return (
    <form className={estilos.tarjeta} onSubmit={(evento) => void enviar(evento)} noValidate aria-labelledby="titulo-contrasena">
      <h1 id="titulo-contrasena">Acceso de convenio</h1>
      <p>Ingresa la contraseña que te entregó la empresa de transporte.</p>
      {vencida && <Aviso>Tu sesión venció. Ingresa de nuevo la contraseña.</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <Campo etiqueta="Contraseña" error={faltante ? 'Ingresa la contraseña.' : undefined}>
        {(control) => <input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} {...control} />}
      </Campo>
      <button type="submit" className={estilos.botonPrincipal} disabled={entrar.isPending}>
        {entrar.isPending ? 'Entrando…' : 'Entrar'}
      </button>
    </form>
  );
}

interface Enviada {
  cuerpo: Solicitud;
  respuesta: { recogida_en: string; mensaje: string };
}

function ConSesion({ api, token, acceso, alNoDisponible, alVencer }: { api: ClientePortal; token: string; acceso: Acceso; alNoDisponible: () => void; alVencer: () => void }) {
  const solicitar = useSolicitarConvenio(api, token);
  const salir = useSalirConvenio(api, token);
  const [enviada, setEnviada] = useState<Enviada | null>(null);
  const [vuelta, setVuelta] = useState(0);

  return (
    <>
      {enviada ? (
        <Confirmacion
          {...enviada}
          destacado={
            <>
              Reserva registrada a nombre de <strong>{acceso.cliente_nombre}</strong>. No requiere confirmación por WhatsApp.
            </>
          }
          alHacerOtra={() => {
            setEnviada(null);
            setVuelta((n) => n + 1);
          }}
        />
      ) : (
        <FormularioSolicitud
          key={vuelta}
          empresa={acceso}
          solicitar={solicitar.mutateAsync}
          intro={`La reserva queda a nombre de ${acceso.cliente_nombre}, sin confirmación por WhatsApp.`}
          leyendaDatos="Datos del pasajero"
          alEnviar={setEnviada}
          alNoDisponible={alNoDisponible}
          alVencerSesion={alVencer}
        />
      )}
      {salir.isError && <Aviso tipo="error">No se pudo cerrar la sesión. Intenta de nuevo.</Aviso>}
      <div className={`${estilos.acciones} ${estilos.salir}`}>
        <button type="button" className={estilos.botonSecundario} disabled={salir.isPending} onClick={() => salir.mutate()}>
          Salir
        </button>
      </div>
    </>
  );
}
