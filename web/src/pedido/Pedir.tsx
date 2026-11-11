import { useMutation, useQuery } from '@tanstack/react-query';
import { useEffect, useState, useSyncExternalStore } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
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
import { esTipo, TIPOS, type CuerpoPedido, type TipoPedido } from './pedido';

const SCL = { lat: -33.393, lng: -70.794 };
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
  const [enviado, setEnviado] = useState<CuerpoPedido | null>(null);
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

  useEffect(() => {
    document.title = `Pedir traslado · ${usuario?.empresa.razon_social ?? 'FlotaÁgil'}`;
  }, [usuario?.empresa.razon_social]);

  if (!usuario) return null;
  if (usuario.rol !== 'PASAJERO') return <Navigate to={inicioDeRol(usuario.rol)} replace />;
  if (parametro !== undefined && !esTipo(parametro)) return <Navigate to="/pedir" replace />;

  const tipo: TipoPedido | null = esTipo(parametro) ? parametro : angosto ? null : 'desde-aeropuerto';
  const enlaces = [
    { a: '/pedir', texto: 'Pedir traslado' },
    { a: '/mis-reservas', texto: 'Mis viajes' },
  ];
  const salir = () => void sesion.logout().then(() => navegar(`/solicitar/${slug}/ingresar`, { replace: true }));

  let panel;
  if (empresa.isPending) panel = <Cargando />;
  else if (empresa.isError) panel = <Aviso tipo="error">No pudimos cargar los datos de tu empresa. Recarga la página.</Aviso>;
  else if (enviado) {
    panel = (
      <div className={e.formulario}>
        <h1 className={e.tituloPagina}>Recibimos tu pedido</h1>
        <Destacado titulo="Te avisaremos por WhatsApp" icono="mensaje">
          Cuando la central te asigne un conductor, te llegará su nombre y la patente del vehículo.
        </Destacado>
        <Link to="/mis-reservas" className={claseBoton('principal', true)}>
          Ver mis viajes
        </Link>
        <button type="button" className={claseBoton('texto')} onClick={() => setEnviado(null)}>
          Pedir otro traslado
        </button>
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
    const formulario = (
      <FormularioPedido key={tipo} tipo={tipo} empresa={empresa.data} enviar={pedir.mutateAsync} alEnviar={setEnviado} />
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

  const conFormulario = tipo !== null && !enviado;
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
