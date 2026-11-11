import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Link, useParams } from 'react-router';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaAcceso, Separador } from '../diseno/PantallaAcceso';
import { useApi } from '../sesion/SesionProvider';
import { useIngreso } from './ingreso';

/**
 * Ingreso del portal (HU-38) en /solicitar/:slug/ingresar, con la marca de la empresa: mapa y panel inferior en
 * el celular. Misma lógica de HU-33 que /login. Vive bajo la raíz de sesión (el marco del portal no la carga),
 * así que no importa nada de src/portal/: la empresa se consulta aquí.
 */
export function IngresarPortal() {
  const { slug = '' } = useParams();
  const api = useApi();
  const { bloqueo, aviso, error, formulario, enviar } = useIngreso();
  const empresa = useQuery({
    queryKey: ['portal', 'empresa', slug],
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug } } })),
    retry: false,
    staleTime: 5 * 60_000,
  });
  const marca = empresa.data?.razon_social ?? 'FlotaÁgil';
  const {
    register,
    formState: { errors, isSubmitting },
  } = formulario;

  useEffect(() => {
    document.title = `Ingresar · ${marca}`;
  }, [marca]);

  if (bloqueo) return bloqueo;

  const registro = empresa.data ? { a: `/solicitar/${slug}/registro-empresa`, texto: '¿Eres empresa? Registra tu convenio' } : undefined;

  return (
    <MarcoPortal marca={marca} inicio={`/solicitar/${slug}/ingresar`} barraMovil="flotante" accion={registro}>
      <PantallaAcceso titulo="Ingresar" tituloMovil="Tu traslado, sin esperas" subtitulo="Ingresa para pedir y seguir tus viajes." movil="mapa">
        {empresa.isError && <Aviso tipo="error">Esta empresa no tiene un portal disponible. Revisa el enlace que te enviaron.</Aviso>}
        <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Ingresar">
          {aviso && <Aviso>{aviso}</Aviso>}
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
          <Link to={`/recuperar?empresa=${slug}`} className={`${e.enlace} ${e.derecha}`}>
            ¿Olvidaste tu contraseña?
          </Link>
          <Boton type="submit" ancho cargando={isSubmitting}>
            {isSubmitting ? 'Ingresando…' : 'Ingresar'}
          </Boton>
          {error && empresa.data && (
            <p className={e.nota}>
              ¿Creaste tu cuenta y no la activaste?{' '}
              <Link to={`/solicitar/${slug}/activar`} className={e.enlace}>
                Activa tu cuenta
              </Link>
            </p>
          )}
        </form>
        {empresa.data && (
          <>
            <div className={e.soloEscritorio}>
              <Separador>¿No tienes cuenta?</Separador>
            </div>
            <Link to={`/solicitar/${slug}/cuenta`} className={claseBoton('secundario', true)}>
              Crear cuenta
            </Link>
          </>
        )}
        {registro && (
          <Link to={registro.a} className={`${e.enlace} ${e.soloMovil}`}>
            {registro.texto}
          </Link>
        )}
      </PantallaAcceso>
    </MarcoPortal>
  );
}
