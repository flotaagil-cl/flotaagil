import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Aviso } from '../componentes/Aviso';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import type { NombreIcono } from '../diseno/iconos';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaAcceso } from '../diseno/PantallaAcceso';
import { Insignia } from '../diseno/Tarjeta';
import { useApi } from '../sesion/SesionProvider';
import { resultado } from '../api/resultado';
import { useIngreso } from './ingreso';

const PUNTOS: [NombreIcono, string][] = [
  ['lista', 'Reservas y asignación en tiempo real'],
  ['auto', 'Fila del aeropuerto por orden de llegada'],
  ['avion', 'Seguimiento de vuelos automático'],
];

/** Panel con el degradé del ingreso del panel. La mini vista es una ilustración con datos de ejemplo. */
function HeroPanel() {
  return (
    <>
      <p className={e.heroAntetitulo}>Panel de operación</p>
      <p className={e.heroTitulo}>La operación de tu flota, en un solo lugar.</p>
      <ul className={e.heroPuntos}>
        {PUNTOS.map(([icono, texto]) => (
          <li key={texto}>
            <span className={e.heroPuntoIcono}>
              <Icono nombre={icono} tamano={16} />
            </span>
            {texto}
          </li>
        ))}
      </ul>
      <div className={e.miniVista} aria-hidden="true">
        <div className={e.miniTarjetas}>
          {[
            ['Reservas de hoy', '38'],
            ['Sin asignar', '3'],
            ['En fila', '4'],
          ].map(([etiqueta, valor]) => (
            <div key={etiqueta} className={e.miniTarjeta}>
              <span className={e.miniEtiqueta}>{etiqueta}</span>
              <span className={e.miniValor}>{valor}</span>
            </div>
          ))}
        </div>
        <div className={e.miniVuelo}>
          <Icono nombre="avion" tamano={16} />
          <span>LA 845 · LIM → SCL</span>
          <Insignia tono="revision">Atrasado 25 min</Insignia>
        </div>
      </div>
    </>
  );
}

/**
 * Ingreso del panel (/login) con la marca de FlotaÁgil (docs/diseno/panel/00-login.png). Sigue siendo el inicio
 * de sesión único de HU-33: acepta todos los roles y cada uno llega a su vista. Los pasajeros y convenios
 * tienen su ingreso con la marca de la empresa en /solicitar/:slug/ingresar.
 */
export function Login() {
  const { bloqueo, aviso, error, formulario, enviar } = useIngreso();
  const api = useApi();
  // SOPORTE_CORREO del servidor: sin correo configurado no se muestra el enlace.
  const configuracion = useQuery({
    queryKey: ['configuracion-publica'],
    queryFn: () => resultado(api.GET('/api/configuracion-publica/')),
    retry: false,
    staleTime: 60 * 60_000,
  });
  const soporte = configuracion.data?.soporte_correo ?? null;
  const {
    register,
    formState: { errors, isSubmitting },
  } = formulario;

  useEffect(() => {
    document.title = 'Ingresar al panel · FlotaÁgil';
  }, []);

  if (bloqueo) return bloqueo;

  return (
    <MarcoPortal
      marca="FlotaÁgil"
      inicio="/login"
      logo={<Icono nombre="auto" />}
      accion={soporte ? { a: `mailto:${soporte}`, texto: 'Soporte', externo: true } : undefined}
    >
      <PantallaAcceso
        titulo="Ingresar al panel"
        subtitulo="Para administradores y despachadores de empresas de transporte."
        movil="centrado"
        hero={<HeroPanel />}
      >
        <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Ingresar al panel">
          {aviso && <Aviso>{aviso}</Aviso>}
          {error && <Aviso tipo="error">{error}</Aviso>}
          <Campo
            etiqueta="Correo"
            type="email"
            autoComplete="username"
            inputMode="email"
            placeholder="nombre@empresa.cl"
            error={errors.email?.message}
            {...register('email')}
          />
          <Campo etiqueta="Contraseña" type="password" autoComplete="current-password" error={errors.password?.message} {...register('password')} />
          <Boton type="submit" ancho cargando={isSubmitting}>
            {isSubmitting ? 'Ingresando…' : 'Ingresar'}
          </Boton>
        </form>
        <p className={e.avisoSuave}>
          <Icono nombre="llave" tamano={18} />
          <span>
            ¿Olvidaste tu contraseña? Pídele una temporal al administrador de tu empresa. Si eres el administrador, escríbenos a{' '}
            {soporte ? <a href={`mailto:${soporte}`}>soporte</a> : 'soporte'}.
          </span>
        </p>
        <hr className={e.divisor} />
        <p className={e.notaIzquierda}>¿Eres pasajero o empresa en convenio? Entra desde el enlace de tu empresa de transporte.</p>
      </PantallaAcceso>
    </MarcoPortal>
  );
}
