import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, Outlet, useMatches, useParams } from 'react-router';
import { ErrorApi } from '../api/resultado';
import { MENSAJES } from '../api/errores';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { useTitulo } from '../diseno/titulo';
import { useEntorno } from '../entornoContexto';
import { ContactoDeError } from '../componentes/ContactoDeError';
import { crearClientePortal, useEmpresa, type ClientePortal } from './api';
import { guardarCentral } from '../componentes/central';
import type { ContextoPortal } from './contexto';
import { NoDisponible } from './NoDisponible';
import estilos from './portal.module.css';

/**
 * Marco público del portal (/solicitar/:slug): sin sesión ni refresh silencioso. Carga la empresa por su slug
 * y muestra su nombre; si no existe o está inactiva, una página clara en vez del formulario. Desde HU-38 usa el
 * marco del sistema visual; una ruta puede ocultar la barra en el celular con `handle.barraMovil`.
 */
export function LayoutPortal() {
  const entorno = useEntorno();
  const [{ api, cliente }] = useState(() => ({
    api: crearClientePortal(entorno),
    cliente: new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }),
  }));
  return (
    <QueryClientProvider client={cliente}>
      <ContenidoPortal api={api} />
    </QueryClientProvider>
  );
}

function ContenidoPortal({ api }: { api: ClientePortal }) {
  const { slug = '' } = useParams();
  const { almacen } = useEntorno();
  const empresa = useEmpresa(api, slug);
  const central = empresa.data?.central;
  const razonSocial = empresa.data?.razon_social;
  const matches = useMatches();
  const manejo = matches.at(-1)?.handle as
    | { titulo?: string; barraMovil?: 'normal' | 'oculta'; completa?: boolean; requiereModulo?: boolean; soloSinModulo?: boolean }
    | undefined;
  // DC-51 (CC-22): crear cuenta, activarla y registrar empresa existen solo con el módulo de cuentas.
  const sinModulo = empresa.data !== undefined && !empresa.data.modulo_cuentas;
  const barraMovil = manejo?.barraMovil ?? 'normal';

  // HU-49 (DC-80): los números de la central quedan guardados para cuando el servidor no responda.
  useEffect(() => {
    if (central) guardarCentral(almacen, slug, central);
  }, [almacen, slug, central]);

  const errorEstado = empresa.error instanceof ErrorApi ? empresa.error.estado : 0;
  const tituloPortal = empresa.isError
    ? errorEstado === 404
      ? 'Portal no disponible'
      : 'Error de conexión'
    : (manejo?.titulo ?? (empresa.data ? (sinModulo ? 'Pedir un traslado' : 'Pide tu traslado') : 'Solicitar un viaje'));
  useTitulo(tituloPortal, razonSocial);

  let contenido;
  if (empresa.isPending) {
    contenido = (
      <div className={estilos.esqueleto} role="status" aria-label="Cargando">
        <span />
        <span />
        <span />
      </div>
    );
  } else if (empresa.isError) {
    const estado = empresa.error instanceof ErrorApi ? empresa.error.estado : 0;
    const delServidor = estado === 500 || (estado > 504 && estado < 600);
    contenido =
      estado === 404 ? (
        <NoDisponible />
      ) : (
        <section className={estilos.tarjeta} role="alert">
          <h1>{delServidor ? 'El servidor tuvo un error' : 'No se pudo conectar con el servidor'}</h1>
          <p>{delServidor ? MENSAJES.error_servidor : MENSAJES.sin_conexion}</p>
          <button type="button" className={estilos.botonPrincipal} onClick={() => void empresa.refetch()}>
            Reintentar
          </button>
          <ContactoDeError />
        </section>
      );
  } else if ((sinModulo && manejo?.requiereModulo) || (empresa.data?.modulo_cuentas && manejo?.soloSinModulo)) {
    contenido = <NoDisponible />;
  } else contenido = <Outlet context={{ api, empresa: empresa.data, slug } satisfies ContextoPortal} />;

  // DC-51: con el módulo, registro con cuenta (HU-34); sin él, solicitud pública de convenio (HU-53).
  const registro = sinModulo ? `/solicitar/${slug}/convenio` : `/solicitar/${slug}/registro-empresa`;
  return (
    <MarcoPortal
      marca={razonSocial ?? 'FlotaÁgil'}
      inicio={sinModulo ? `/solicitar/${slug}` : `/solicitar/${slug}/ingresar`}
      barraMovil={barraMovil}
      accion={empresa.data && !ubicacionEs(matches, registro) ? { a: registro, texto: sinModulo ? '¿Eres empresa? Solicita un convenio' : '¿Eres empresa? Registra tu convenio' } : undefined}
      pie={
        <>
          {empresa.data && <Link to={`/solicitar/${slug}/privacidad`}>Aviso de privacidad</Link>}
          <span>Operado con FlotaÁgil</span>
        </>
      }
    >
      {/* Las pantallas con el diseño nuevo ocupan el ancho completo; las anteriores, la columna angosta. */}
      {manejo?.completa && empresa.data ? contenido : <div className={estilos.contenido}>{contenido}</div>}
    </MarcoPortal>
  );
}

function ubicacionEs(matches: ReturnType<typeof useMatches>, ruta: string): boolean {
  return matches.at(-1)?.pathname.replace(/\/$/, '') === ruta;
}
