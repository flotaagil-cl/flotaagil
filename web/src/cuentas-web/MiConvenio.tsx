import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import { Link, Navigate, useNavigate } from 'react-router';
import type { components } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { Pestanas } from '../diseno/Pestanas';
import { Insignia, Tarjeta, type TonoInsignia } from '../diseno/Tarjeta';
import { useEntorno } from '../entornoContexto';
import { formatearFechaHora } from '../hora/hora';
import { FormularioPedido } from '../pedido/FormularioPedido';
import { erroresDelServidor, resumenPedido, TIPOS, type CuerpoPedido, type Errores, type TipoPedido, type ValoresPedido } from '../pedido/pedido';
import { guardarCentral } from '../componentes/central';
import { inicioDeRol } from '../rutas/tabla';
import { cuerpoPersonas, DATOS_CONVENIO, erroresConvenioDelServidor, validarConvenio, type DatosConvenio, type ErroresConvenio } from '../portal/convenio';
import { PersonasConvenio } from '../portal/PersonasConvenio';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { BotonesCentral } from '../componentes/BotonesCentral';
import { esAnterior, INSIGNIA, tramo } from '../viajes/viaje';

type MiConvenioDatos = components['schemas']['MiConvenio'];
type EstadoConvenio = MiConvenioDatos['estado'];

/** Navegación de la cuenta del convenio (HU-46). */
const ENLACES_CONVENIO = [
  { a: '/mi-convenio', texto: 'Pedir traslado' },
  { a: '/mi-convenio/viajes', texto: 'Viajes del convenio' },
];

const ESTADO: Partial<Record<NonNullable<EstadoConvenio>, { texto: string; tono: TonoInsignia }>> = {
  EN_REVISION: { texto: 'En revisión', tono: 'revision' },
  RECHAZADO: { texto: 'Rechazado', tono: 'peligro' },
  INACTIVO: { texto: 'Inactivo', tono: 'neutra' },
};

function useMiConvenio() {
  const api = useApi();
  return useQuery({ queryKey: ['mi-convenio'], queryFn: () => resultado(api.GET('/api/mi-convenio/')) });
}

/** Datos públicos de la empresa (capacidad, márgenes y la central): los usan el formulario y el contacto. */
function useEmpresa(slug: string) {
  const api = useApi();
  const { almacen } = useEntorno();
  const empresa = useQuery({
    queryKey: ['portal', 'empresa', slug],
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug } } })),
    enabled: Boolean(slug),
    staleTime: 5 * 60_000,
  });
  const central = empresa.data?.central;
  // HU-49 (DC-80): los números quedan guardados para las pantallas de error.
  useEffect(() => {
    if (central) guardarCentral(almacen, slug, central);
  }, [almacen, slug, central]);
  return empresa;
}

/** Marco de la cuenta del convenio con la marca de la empresa de taxis (HU-46, sistema visual de CC-20). */
function MarcoConvenio({ children }: { children: ReactNode }) {
  const { estado, sesion } = useSesion();
  const navegar = useNavigate();
  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  const salir = () => void sesion.logout().then(() => navegar(`/solicitar/${usuario.empresa.slug}/ingresar`, { replace: true }));
  return (
    <MarcoPortal marca={usuario.empresa.razon_social} inicio="/mi-convenio" enlaces={ENLACES_CONVENIO} usuario={usuario} onCerrarSesion={salir}>
      <div className={e.paginaAngosta}>{children}</div>
    </MarcoPortal>
  );
}

/** Solo el rol CONVENIO: los demás vuelven a su inicio. */
function useGuardaConvenio(): ReactNode | null {
  const { estado } = useSesion();
  if (estado.fase !== 'autenticada') return <Cargando />;
  if (estado.usuario.rol !== 'CONVENIO') return <Navigate to={inicioDeRol(estado.usuario.rol)} replace />;
  return null;
}

/**
 * HU-34 y HU-46: la cuenta de la empresa cliente. En revisión o rechazada ve una tarjeta con su estado; aprobada
 * pide traslados: el viaje (el mismo formulario del pasajero), quién viaja y el pedido recibido. HU-47 (CC-25):
 * quien pide, para sí o para otra persona, con acompañantes en el mismo vehículo o en vehículos separados.
 */
export function MiConvenio() {
  const guarda = useGuardaConvenio();
  const convenio = useMiConvenio();
  useEffect(() => {
    document.title = 'Mi convenio';
  }, []);
  if (guarda) return guarda;
  return (
    <MarcoConvenio>
      {convenio.isPending ? (
        <Cargando />
      ) : convenio.isError ? (
        <Aviso tipo="error">No pudimos cargar tu convenio. Recarga la página.</Aviso>
      ) : convenio.data.estado === 'APROBADO' ? (
        <PedirTraslado convenio={convenio.data} />
      ) : (
        <TarjetaEstado convenio={convenio.data} />
      )}
    </MarcoConvenio>
  );
}

function TarjetaEstado({ convenio }: { convenio: MiConvenioDatos }) {
  const empresa = useEmpresa(convenio.empresa_slug);
  const insignia = ESTADO[convenio.estado ?? 'EN_REVISION'] ?? ESTADO.EN_REVISION!;
  return (
    <>
      <div className={e.tituloConInsignia}>
        <h1 className={e.tituloPagina}>Mi convenio</h1>
        <Insignia tono={insignia.tono}>{insignia.texto}</Insignia>
      </div>
      <Tarjeta como="section" aria-label="Estado del convenio">
        <p className={e.opcionTitulo}>{convenio.cliente_nombre}</p>
        <p className={e.opcionDetalle}>Convenio con {convenio.empresa}</p>
        {convenio.estado === 'RECHAZADO' ? (
          <>
            <p>{convenio.empresa} no aprobó el convenio.</p>
            {convenio.motivo_rechazo && <p>Motivo: {convenio.motivo_rechazo}</p>}
            <p>Si crees que es un error, contacta a la central.</p>
          </>
        ) : (
          <p>Tu registro está en revisión. Te avisaremos por correo cuando {convenio.empresa} lo apruebe; mientras tanto no puedes pedir traslados.</p>
        )}
      </Tarjeta>
      <BotonesCentral central={empresa.data?.central} />
    </>
  );
}

type Etapa =
  | { fase: 'formulario'; valores?: ValoresPedido; errores?: Errores }
  | { fase: 'quien'; tipo: TipoPedido; valores: ValoresPedido; cuerpo: CuerpoPedido }
  | { fase: 'recibido'; mensaje: string; viajes: number };

/** Quien pide (CC-25): queda como solicitante de los viajes. */
interface Solicitante {
  nombre: string;
  telefono: string;
}

type ErroresSolicitante = Partial<Record<keyof Solicitante | 'general', string>>;

const SOLICITANTE: Solicitante = { nombre: '', telefono: '' };

function primero(valor: unknown): string | undefined {
  return Array.isArray(valor) ? String(valor[0]) : typeof valor === 'string' ? valor : undefined;
}

function PedirTraslado({ convenio }: { convenio: MiConvenioDatos }) {
  const api = useApi();
  const empresa = useEmpresa(convenio.empresa_slug);
  const [tipo, setTipo] = useState<TipoPedido>('desde-aeropuerto');
  const [etapa, setEtapa] = useState<Etapa>({ fase: 'formulario' });
  const [solicitante, setSolicitante] = useState<Solicitante>(SOLICITANTE);
  const [personas, setPersonas] = useState<DatosConvenio>(DATOS_CONVENIO);
  const [errores, setErrores] = useState<ErroresSolicitante>({});
  const [erroresPersonas, setErroresPersonas] = useState<ErroresConvenio>({});
  const pedir = useMutation({
    mutationFn: (cuerpo: CuerpoPedido) => {
      // CC-25: las mismas personas que CC-23, sin pase ni datos de empresa.
      return resultado(
        api.POST('/api/mi-convenio/solicitudes/', {
          body: { ...cuerpo, ...cuerpoPersonas(personas), nombre: solicitante.nombre.trim(), telefono: solicitante.telefono.trim() },
        }),
      );
    },
  });

  if (empresa.isPending) return <Cargando />;
  if (empresa.isError) return <Aviso tipo="error">No pudimos cargar los datos de la empresa. Recarga la página.</Aviso>;

  if (etapa.fase === 'recibido') {
    return (
      <div className={e.recibido}>
        <span className={e.recibidoMarca} aria-hidden="true">
          <Icono nombre="check" tamano={36} />
        </span>
        <h1 className={e.tituloPagina}>{etapa.viajes > 1 ? `¡Listo! Recibimos ${etapa.viajes} viajes` : '¡Listo! Recibimos el pedido'}</h1>
        <p className={e.subtituloPagina}>{etapa.mensaje}</p>
        <Link to="/mi-convenio/viajes" className={claseBoton('principal', true)}>
          Ver los viajes del convenio
        </Link>
        <button
          type="button"
          className={e.botonEnlace}
          onClick={() => {
            setSolicitante(SOLICITANTE);
            setPersonas(DATOS_CONVENIO);
            setEtapa({ fase: 'formulario' });
          }}
        >
          Pedir otro traslado
        </button>
      </div>
    );
  }

  if (etapa.fase === 'quien') {
    const actual = TIPOS.find((t) => t.id === etapa.tipo)!;
    const cambiar = <K extends keyof Solicitante>(campo: K, valor: Solicitante[K]) => setSolicitante((p) => ({ ...p, [campo]: valor }));
    const capacidad = empresa.data.capacidad_maxima;
    const tope = empresa.data.convenio_max_personas;
    const enviar = async (evento: FormEvent) => {
      evento.preventDefault();
      const encontrados: ErroresSolicitante = {};
      if (!solicitante.nombre.trim()) encontrados.nombre = 'Escribe tu nombre.';
      if (!solicitante.telefono.trim()) encontrados.telefono = 'Escribe tu teléfono.';
      const deGrupo = validarConvenio(personas, capacidad, tope);
      setErrores(encontrados);
      setErroresPersonas(deGrupo);
      if (Object.keys(encontrados).length > 0 || Object.keys(deGrupo).length > 0) return;
      try {
        const respuesta = await pedir.mutateAsync(etapa.cuerpo);
        setEtapa({ fase: 'recibido', mensaje: respuesta.mensaje, viajes: respuesta.viajes });
      } catch (error) {
        if (error instanceof ErrorApi && error.estado === 400) {
          const c = (error.cuerpo ?? {}) as Record<string, unknown>;
          const propios: ErroresSolicitante = { nombre: primero(c.nombre), telefono: primero(c.telefono) };
          const delGrupo = erroresConvenioDelServidor(error.cuerpo);
          if (Object.values(propios).some(Boolean) || Object.keys(delGrupo).length > 0) {
            setErrores(propios);
            setErroresPersonas(delGrupo);
          } else setEtapa({ fase: 'formulario', valores: etapa.valores, errores: erroresDelServidor(error.cuerpo) });
        } else if (error instanceof ErrorApi && error.estado === 409) setErrores({ general: 'Tu convenio ya no está aprobado: no puedes pedir traslados.' });
        else setErrores({ general: 'No se pudo enviar el pedido. Revisa tu conexión e intenta de nuevo.' });
      }
    };
    return (
      <>
        <h1 className={e.tituloPagina}>Quién viaja</h1>
        <section className={e.resumen} aria-label="Tu viaje">
          <h2 className={e.resumenTitulo}>{actual.titulo}</h2>
          <dl className={e.resumenFilas}>
            {resumenPedido(etapa.tipo, etapa.valores, etapa.cuerpo, empresa.data).map(([etiqueta, texto]) => {
              // HU-47: cuántos viajan sale de esta etapa; del viaje solo quedan las maletas.
              const [fila, valor] = etiqueta === 'Pasajeros' ? ['Maletas', String(etapa.cuerpo.maletas ?? 0)] : [etiqueta, texto];
              return (
                <div key={fila}>
                  <dt>{fila}</dt>
                  <dd>{valor}</dd>
                </div>
              );
            })}
          </dl>
          <button type="button" className={e.botonEnlace} onClick={() => setEtapa({ fase: 'formulario', valores: etapa.valores })}>
            Editar el viaje
          </button>
        </section>
        <form className={e.formulario} onSubmit={(ev) => void enviar(ev)} noValidate aria-label="Quién viaja">
          {errores.general && <Aviso tipo="error">{errores.general}</Aviso>}
          <Tarjeta como="section" className={e.formulario}>
            <h2 className={e.resumenTitulo}>Quién pide</h2>
            <Campo etiqueta="Tu nombre" autoComplete="name" value={solicitante.nombre} error={errores.nombre} onChange={(ev) => cambiar('nombre', ev.target.value)} />
            <Campo
              etiqueta="Tu teléfono"
              type="tel"
              autoComplete="tel"
              placeholder="+56912345678"
              value={solicitante.telefono}
              error={errores.telefono}
              ayuda="La central te llama si hay que coordinar algo."
              onChange={(ev) => cambiar('telefono', ev.target.value)}
            />
          </Tarjeta>
          <PersonasConvenio
            slug={convenio.empresa_slug}
            datos={personas}
            errores={erroresPersonas}
            capacidad={capacidad}
            tope={tope}
            ayudaSeparados="Un vehículo por persona, con el mismo origen, destino y hora. Todos quedan solicitados de inmediato."
            onCambiar={setPersonas}
          />
          <Boton type="submit" ancho cargando={pedir.isPending}>
            {pedir.isPending ? 'Enviando…' : 'Confirmar pedido'}
          </Boton>
        </form>
      </>
    );
  }

  const borrador = etapa;
  return (
    <>
      <h1 className={e.tituloPagina}>¿A dónde llevamos a tu equipo?</h1>
      <p className={e.subtituloPagina}>
        Pide traslados a nombre de {convenio.cliente_nombre}: quedan solicitados de inmediato y la central asigna el conductor.
      </p>
      <Pestanas etiqueta="Tipo de viaje" pestanas={TIPOS} activa={tipo} onCambiar={(id) => setTipo(id as TipoPedido)}>
        <FormularioPedido
          key={`${tipo}-${borrador.valores ? 'borrador' : 'nuevo'}`}
          tipo={tipo}
          empresa={empresa.data}
          iniciales={borrador.valores}
          erroresIniciales={borrador.errores}
          sinPasajeros
          textoBoton="Siguiente: quién viaja"
          nota={<>Sigue los pedidos en «Viajes del convenio».</>}
          alRevisar={(valores, cuerpo) => {
            setErrores({});
            setEtapa({ fase: 'quien', tipo, valores, cuerpo });
          }}
        />
      </Pestanas>
    </>
  );
}

/** HU-46: los viajes del convenio, próximos y anteriores, como tarjetas (igual que «Mis viajes» del pasajero). */
export function ViajesDelConvenio() {
  const guarda = useGuardaConvenio();
  const api = useApi();
  const reservas = useQuery({ queryKey: ['mi-convenio', 'reservas'], queryFn: () => resultado(api.GET('/api/mi-convenio/reservas/')) });
  useEffect(() => {
    document.title = 'Viajes del convenio';
  }, []);
  if (guarda) return guarda;
  const todos = reservas.data?.results ?? [];
  const proximos = todos.filter((v) => !esAnterior(v.estado)).sort((a, b) => a.recogida_en.localeCompare(b.recogida_en));
  const anteriores = todos.filter((v) => esAnterior(v.estado));
  return (
    <MarcoConvenio>
      <div className={e.tituloConInsignia}>
        <h1 className={e.tituloPagina}>Viajes del convenio</h1>
        <Link to="/mi-convenio" className={claseBoton('principal')}>
          Pedir traslado
        </Link>
      </div>
      {reservas.isPending && <Cargando />}
      {reservas.isError && <Aviso tipo="error">No pudimos cargar los viajes. Recarga la página.</Aviso>}
      {reservas.isSuccess && todos.length === 0 && <p className={e.saludo}>Aún no hay viajes con tu convenio.</p>}
      <ListaViajes titulo="Próximos" viajes={proximos} />
      <ListaViajes titulo="Anteriores" viajes={anteriores} />
    </MarcoConvenio>
  );
}

function ListaViajes({ titulo, viajes }: { titulo: string; viajes: components['schemas']['ReservaDelConvenio'][] }) {
  if (viajes.length === 0) return null;
  return (
    <section aria-label={titulo}>
      <h2 className={e.resumenTitulo}>{titulo}</h2>
      <ul className={e.listaViajes}>
        {viajes.map((v) => {
          const insignia = INSIGNIA[v.estado ?? 'SOLICITADO'];
          return (
            <li key={v.id}>
              <div className={e.opcionViaje}>
                <span className={e.opcionIcono}>
                  <Icono nombre={v.sentido === 'DESDE_AEROPUERTO' ? 'aterrizaje' : v.sentido === 'HACIA_AEROPUERTO' ? 'despegue' : 'auto'} />
                </span>
                <span className={e.viajeTexto}>
                  <span className={e.opcionTitulo}>{tramo(v)}</span>
                  <span className={e.opcionDetalle}>
                    {v.pasajero} · {formatearFechaHora(v.recogida_en)} · N.º {v.id}
                  </span>
                </span>
                <Insignia tono={insignia.tono}>{insignia.texto}</Insignia>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
