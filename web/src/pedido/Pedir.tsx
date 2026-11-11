import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState, useSyncExternalStore } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { Boton } from '../diseno/Boton';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import type { NombreIcono } from '../diseno/iconos';
import { Mapa } from '../diseno/mapa/Mapa';
import type { PropsMapa } from '../diseno/mapa/tipos';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaConMapa } from '../diseno/PantallaConMapa';
import { Pestanas } from '../diseno/Pestanas';
import { Destacado } from '../diseno/Tarjeta';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { FormularioPedido } from './FormularioPedido';
import { ErrorApi } from '../api/resultado';
import { mostrarTelefono } from '../portal/telefono';
import { erroresDelServidor, esTipo, resumenPedido, TIPOS, type CuerpoPedido, type Errores, type TipoPedido, type ValoresPedido } from './pedido';

const SCL = { lat: -33.393, lng: -70.794 };

type Etapa =
  | { fase: 'formulario'; valores?: ValoresPedido; errores?: Errores }
  | { fase: 'revision'; tipo: TipoPedido; valores: ValoresPedido; cuerpo: CuerpoPedido }
  | { fase: 'recibido'; id: number };
const ICONOS: Record<TipoPedido, NombreIcono> = { 'desde-aeropuerto': 'aterrizaje', 'al-aeropuerto': 'despegue', 'en-la-ciudad': 'auto' };
const ANGOSTO = '(max-width: 899px)';

/** En el celular el inicio muestra las tres opciones; en el computador, las pestañas. */
function useAngosto(): boolean {
  return useSyncExternalStore(
    (avisar) => {
      const consulta = window.matchMedia?.(ANGOSTO);
      consulta?.addEventListener('change', avisar);
      return () => consulta?.removeEventListener('change', avisar);
    },
    () => window.matchMedia?.(ANGOSTO).matches ?? false,
  );
}

function mapaDe(tipo: TipoPedido | null): PropsMapa {
  if (tipo === 'en-la-ciudad') return { etiqueta: 'Mapa de Santiago', marcadores: [] };
  return {
    etiqueta: 'Mapa con el aeropuerto de Santiago',
    marcadores: [{ id: 'scl', punto: SCL, tipo: 'aeropuerto', etiqueta: 'Aeropuerto de Santiago (SCL)' }],
  };
}

/**
 * HU-39: inicio y pedido del pasajero con cuenta (/pedir y /pedir/:tipo), con el marco del portal y la marca de
 * su empresa. En el computador, pestañas con los tres tipos; en el celular, el inicio con las tres opciones y
 * cada formulario en su pantalla. Envía a `POST /api/mi-cuenta/solicitudes/` (HU-40: solo con cuenta).
 */
export function Pedir() {
  const { estado, sesion } = useSesion();
  const api = useApi();
  const navegar = useNavigate();
  const { tipo: parametro } = useParams();
  const angosto = useAngosto();
  // HU-42: formulario → «Revisa tu pedido» → «Pedido recibido».
  const [etapa, setEtapa] = useState<Etapa>({ fase: 'formulario' });
  const [falla, setFalla] = useState<string | null>(null);
  const usuario = estado.fase === 'autenticada' ? estado.usuario : null;
  const slug = usuario?.empresa.slug ?? '';
  const empresa = useQuery({
    queryKey: ['portal', 'empresa', slug],
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug } } })),
    enabled: Boolean(slug),
    staleTime: 5 * 60_000,
  });
  const pedir = useMutation({
    mutationFn: (cuerpo: CuerpoPedido) => resultado(api.POST('/api/mi-cuenta/solicitudes/', { body: cuerpo })),
  });
  const cuenta = useQuery({
    queryKey: ['mi-cuenta'],
    queryFn: () => resultado(api.GET('/api/mi-cuenta/')),
    enabled: usuario?.rol === 'PASAJERO',
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    document.title = `Pedir traslado · ${usuario?.empresa.razon_social ?? 'FlotaÁgil'}`;
  }, [usuario?.empresa.razon_social]);

  if (!usuario) return null;
  if (usuario.rol !== 'PASAJERO') return <Navigate to={inicioDeRol(usuario.rol)} replace />;
  if (parametro !== undefined && !esTipo(parametro)) return <Navigate to="/pedir" replace />;

  const tipo: TipoPedido | null = esTipo(parametro) ? parametro : angosto ? null : 'desde-aeropuerto';
  const revisando = etapa.fase === 'revision' && etapa.tipo === tipo ? etapa : null;
  const volverAlFormulario = (cambios: Partial<Extract<Etapa, { fase: 'formulario' }>> = {}) =>
    setEtapa({ fase: 'formulario', valores: revisando?.valores, ...cambios });

  async function confirmar() {
    if (!revisando) return;
    setFalla(null);
    try {
      const respuesta = await pedir.mutateAsync(revisando.cuerpo);
      setEtapa({ fase: 'recibido', id: respuesta.id });
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) volverAlFormulario({ errores: erroresDelServidor(error.cuerpo) });
      else if (error instanceof ErrorApi && error.estado === 429) setFalla('Ya pediste varios traslados hace poco. Espera unos minutos e intenta de nuevo.');
      else setFalla('No se pudo enviar tu pedido. Revisa tu conexión e intenta de nuevo.');
    }
  }
  const enlaces = [
    { a: '/pedir', texto: 'Pedir traslado' },
    { a: '/mis-reservas', texto: 'Mis viajes' },
  ];
  const salir = () => void sesion.logout().then(() => navegar(`/solicitar/${slug}/ingresar`, { replace: true }));

  let panel;
  if (empresa.isPending) panel = <Cargando />;
  else if (empresa.isError) panel = <Aviso tipo="error">No pudimos cargar los datos de tu empresa. Recarga la página.</Aviso>;
  else if (etapa.fase === 'recibido') {
    panel = null;
  } else if (revisando) {
    const actual = TIPOS.find((t) => t.id === revisando.tipo)!;
    panel = (
      <div className={e.formulario}>
        <div>
          <h1 className={e.tituloPagina}>Revisa tu pedido</h1>
          <p className={e.subtituloPagina}>Confirma que todo esté bien antes de enviarlo.</p>
        </div>
        <section className={e.resumen} aria-labelledby="resumen-titulo">
          <h2 id="resumen-titulo" className={e.resumenTitulo}>
            <Icono nombre={ICONOS[revisando.tipo]} /> {actual.titulo}
          </h2>
          <dl className={e.resumenFilas}>
            {resumenPedido(revisando.tipo, revisando.valores, revisando.cuerpo, empresa.data).map(([etiqueta, valor]) => (
              <div key={etiqueta}>
                <dt>{etiqueta}</dt>
                <dd>{valor}</dd>
              </div>
            ))}
          </dl>
          {cuenta.data && (
            <dl className={`${e.resumenFilas} ${e.resumenCuenta}`}>
              <div>
                <dt>Nombre</dt>
                <dd>{cuenta.data.nombre}</dd>
              </div>
              <div>
                <dt>WhatsApp</dt>
                <dd>{mostrarTelefono(cuenta.data.telefono)}</dd>
              </div>
            </dl>
          )}
        </section>
        {revisando.tipo === 'desde-aeropuerto' && (
          <Destacado titulo="Seguimos tu vuelo por ti">Si se atrasa, tu conductor ya lo sabe. No tienes que avisarnos.</Destacado>
        )}
        {falla && (
          <p className={e.alerta} role="alert">
            {falla}
          </p>
        )}
        <Boton ancho cargando={pedir.isPending} onClick={() => void confirmar()}>
          {pedir.isPending ? 'Enviando…' : 'Confirmar pedido'}
        </Boton>
        <Boton variante="secundario" ancho onClick={() => volverAlFormulario()}>
          Editar datos
        </Boton>
      </div>
    );
  } else if (tipo === null) {
    panel = (
      <div className={e.formulario}>
        <div>
          <p className={e.saludo}>Hola, {usuario.nombre.split(' ')[0]}</p>
          <h1 className={e.tituloPagina}>¿Qué viaje necesitas?</h1>
        </div>
        <nav aria-label="Tipo de viaje" className={e.formulario}>
          {TIPOS.map((t) => (
            <Link key={t.id} to={`/pedir/${t.id}`} className={e.opcionViaje}>
              <span className={e.opcionIcono}>
                <Icono nombre={ICONOS[t.id]} />
              </span>
              <span>
                <span className={e.opcionTitulo}>{t.titulo}</span>
                <span className={e.opcionDetalle}>{t.detalle}</span>
              </span>
              <Icono nombre="derecha" />
            </Link>
          ))}
        </nav>
        <Link to="/mis-reservas" className={`${e.enlace} ${e.centrado}`}>
          Mis viajes
        </Link>
      </div>
    );
  } else {
    const borrador: { valores?: ValoresPedido; errores?: Errores } = etapa.fase === 'formulario' ? etapa : {};
    const formulario = (
      <FormularioPedido
        key={`${tipo}-${borrador.valores ? 'borrador' : 'nuevo'}`}
        tipo={tipo}
        empresa={empresa.data}
        iniciales={borrador.valores}
        erroresIniciales={borrador.errores}
        alRevisar={(valores, cuerpo) => {
          setFalla(null);
          setEtapa({ fase: 'revision', tipo, valores, cuerpo });
        }}
      />
    );
    const actual = TIPOS.find((t) => t.id === tipo)!;
    panel = angosto ? (
      <div className={e.formulario}>
        <h1 className={e.tituloPagina}>{actual.titulo}</h1>
        {formulario}
      </div>
    ) : (
      <>
        <h1 className={e.tituloPagina}>¿A dónde te llevamos?</h1>
        <p className={e.subtituloPagina}>Pide tu traslado y te confirmamos por WhatsApp.</p>
        <Pestanas etiqueta="Tipo de viaje" pestanas={TIPOS} activa={tipo} onCambiar={(id) => navegar(`/pedir/${id}`)}>
          {formulario}
        </Pestanas>
      </>
    );
  }

  if (etapa.fase === 'recibido') {
    return (
      <MarcoPortal marca={usuario.empresa.razon_social} inicio="/pedir" enlaces={enlaces} usuario={usuario} onCerrarSesion={salir}>
        <div className={e.recibido}>
          <span className={e.recibidoMarca} aria-hidden="true">
            <Icono nombre="check" tamano={36} />
          </span>
          <h1 className={e.tituloPagina}>¡Listo! Recibimos tu pedido</h1>
          <p className={e.subtituloPagina}>Te avisaremos por WhatsApp cuando la central te asigne un conductor.</p>
          <p className={e.numeroReserva}>
            <span>N.º de reserva</span>
            <strong>{etapa.id}</strong>
          </p>
          <Link to={`/mis-viajes/${etapa.id}`} className={claseBoton('principal', true)}>
            Ver mi viaje
          </Link>
          <button type="button" className={e.botonEnlace} onClick={() => { setEtapa({ fase: 'formulario' }); navegar('/pedir'); }}>
            Volver al inicio
          </button>
        </div>
      </MarcoPortal>
    );
  }

  const conFormulario = tipo !== null;
  return (
    <MarcoPortal
      marca={usuario.empresa.razon_social}
      inicio="/pedir"
      enlaces={enlaces}
      usuario={usuario}
      onCerrarSesion={salir}
      barraMovil={conFormulario ? 'oculta' : 'flotante'}
    >
      <PantallaConMapa
        mapa={<Mapa {...mapaDe(tipo)} />}
        volver={conFormulario ? { a: '/pedir', texto: 'Volver a los tipos de viaje' } : undefined}
        estado={tipo === 'desde-aeropuerto' && conFormulario ? 'SCL · Llegadas' : tipo === 'al-aeropuerto' && conFormulario ? 'SCL · Salidas' : undefined}
      >
        {panel}
      </PantallaConMapa>
    </MarcoPortal>
  );
}
