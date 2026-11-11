import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, Navigate, useSearchParams } from 'react-router';
import { z } from 'zod';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { SinConexion } from '../componentes/SinConexion';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaAcceso, Separador } from '../diseno/PantallaAcceso';
import { useRutas } from '../rutas/contexto';
import { inicioDeRol } from '../rutas/tabla';
import { destinoSeguro } from '../rutas/volver';
import { useApi, useIniciarSesion, useSesion } from '../sesion/SesionProvider';

const esquema = z.object({
  email: z.email({ error: 'Ingresa un correo válido.' }),
  password: z.string().min(1, { error: 'Ingresa tu contraseña.' }),
});

type Datos = z.infer<typeof esquema>;

const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/**
 * Inicio de sesión único de la web (HU-33), con el diseño del portal (HU-38). Con `?empresa=<slug>` (los
 * enlaces del portal lo agregan) muestra la marca de la empresa, «Crear cuenta» y «Registra tu convenio»; sin
 * él, la de FlotaÁgil, para el panel.
 */
export function Login() {
  const estado = useIniciarSesion();
  const { sesion } = useSesion();
  const api = useApi();
  const rutas = useRutas();
  const [parametros] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const slug = SLUG.test(parametros.get('empresa') ?? '') ? parametros.get('empresa')! : null;
  const empresa = useQuery({
    queryKey: ['portal', 'empresa', slug],
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug: slug! } } })),
    enabled: slug !== null,
    retry: false,
    staleTime: 5 * 60_000,
  });
  // Solo con una empresa que existe: un slug cualquiera en el enlace no cambia la marca.
  const conEmpresa = slug !== null && empresa.isSuccess;
  const marca = conEmpresa ? empresa.data.razon_social : 'FlotaÁgil';
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({ resolver: zodResolver(esquema) });

  useEffect(() => {
    document.title = `Ingresar · ${marca}`;
  }, [marca]);

  // No se muestra el formulario hasta saber si ya hay sesión (refresh silencioso).
  if (estado.fase === 'inicial' || estado.fase === 'cargando') return <Cargando />;
  if (estado.fase === 'sin_conexion') {
    return <SinConexion motivo={estado.motivo} alReintentar={() => void sesion.reintentar()} />;
  }
  if (estado.fase === 'autenticada') {
    // HU-33: sin `volver`, cada rol llega a su vista.
    const destino = parametros.get('volver')
      ? destinoSeguro(parametros.get('volver'), rutas, window.location.origin)
      : inicioDeRol(estado.usuario.rol);
    return <Navigate to={destino} replace />;
  }

  async function enviar(datos: Datos) {
    setError(null);
    sesion.descartarAviso();
    const respuesta = await sesion.login(datos.email, datos.password);
    if (!respuesta.ok) setError(respuesta.mensaje);
  }

  const registroEmpresa = conEmpresa ? { a: `/solicitar/${slug}/registro-empresa`, texto: '¿Eres empresa? Registra tu convenio' } : undefined;

  return (
    <MarcoPortal marca={marca} inicio={conEmpresa ? `/login?empresa=${slug}` : '/login'} barraMovil="flotante" accion={registroEmpresa}>
      <PantallaAcceso titulo="Ingresar" tituloMovil="Tu traslado, sin esperas" subtitulo="Ingresa para pedir y seguir tus viajes." movil="mapa">
        <form className={e.formulario} onSubmit={handleSubmit(enviar)} noValidate aria-label="Ingresar">
          {estado.aviso && <Aviso>{estado.aviso}</Aviso>}
          {error && <Aviso tipo="error">{error}</Aviso>}
          <Campo
            etiqueta="Correo"
            type="email"
            autoComplete="username"
            inputMode="email"
            placeholder="nombre@correo.cl"
            error={errors.email?.message}
            {...register('email')}
          />
          <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" error={errors.password?.message} {...register('password')} />
          <Link to="/recuperar" className={`${e.enlace} ${e.derecha}`}>
            ¿Olvidaste tu contraseña?
          </Link>
          <Boton type="submit" ancho cargando={isSubmitting}>
            {isSubmitting ? 'Ingresando…' : 'Ingresar'}
          </Boton>
        </form>
        {conEmpresa && (
          <>
            <div className={e.soloEscritorio}>
              <Separador>¿No tienes cuenta?</Separador>
            </div>
            <Link to={`/solicitar/${slug}/cuenta`} className={claseBoton('secundario', true)}>
              Crear cuenta
            </Link>
          </>
        )}
        <p className={`${e.nota} ${e.soloEscritorio}`}>Administradores, despachadores y empresas en convenio también ingresan por aquí.</p>
        {registroEmpresa && (
          <Link to={registroEmpresa.a} className={`${e.enlace} ${e.soloMovil}`}>
            {registroEmpresa.texto}
          </Link>
        )}
      </PantallaAcceso>
    </MarcoPortal>
  );
}
