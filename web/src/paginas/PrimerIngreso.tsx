import { useEffect, useState, type FormEvent } from 'react';
import { Navigate, useNavigate } from 'react-router';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { PantallaAcceso } from '../diseno/PantallaAcceso';
import { MINIMO_PASSWORD, reglasPassword } from '../diseno/password';
import { ReglasPassword } from '../diseno/ReglasPassword';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';

/** Roles con la marca de su empresa; el personal del panel ve la de FlotaÁgil. */
const DEL_PORTAL = new Set(['PASAJERO', 'CONVENIO']);

/**
 * DC-40 con el diseño de HU-41: primer ingreso con contraseña temporal (DC-14) para todos los roles web. La API
 * responde 403 `cambio_password_requerido` en todo salvo cambiar la contraseña, así que la guarda de rutas trae aquí
 * a quien tenga `debe_cambiar_password`. Al cambiarla, se vuelve a iniciar sesión con la nueva y se sigue a su vista.
 */
export function PrimerIngreso() {
  const { sesion, estado } = useSesion();
  const api = useApi();
  const navegar = useNavigate();
  const [actual, setActual] = useState('');
  const [nueva, setNueva] = useState('');
  const [repetida, setRepetida] = useState('');
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    document.title = 'Crea tu contraseña';
  }, []);

  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  if (!usuario.debe_cambiar_password) return <Navigate to={inicioDeRol(usuario.rol)} replace />;

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados: Record<string, string> = {};
    if (!actual) encontrados.actual = 'Ingresa la contraseña temporal.';
    if (nueva.length < MINIMO_PASSWORD) encontrados.nueva = `Mínimo ${MINIMO_PASSWORD} caracteres.`;
    else if (nueva === actual) encontrados.nueva = 'Debe ser distinta de la temporal.';
    if (repetida !== nueva) encontrados.repetida = 'Las contraseñas no coinciden.';
    setErrores(encontrados);
    setFalla(null);
    if (Object.keys(encontrados).length) return;
    setEnviando(true);
    try {
      await resultado(api.POST('/api/auth/password/', { body: { password_actual: actual, password_nueva: nueva } }));
      const entrada = await sesion.login(usuario.email, nueva);
      if (!entrada.ok) {
        navegar('/login', { replace: true });
        return;
      }
      navegar(inicioDeRol(usuario.rol), { replace: true });
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

  const delPortal = DEL_PORTAL.has(usuario.rol);
  const salida = delPortal ? `/solicitar/${usuario.empresa.slug}/ingresar` : '/login';
  return (
    <MarcoPortal
      marca={delPortal ? usuario.empresa.razon_social : 'FlotaÁgil'}
      logo={delPortal ? undefined : <Icono nombre="auto" />}
      inicio="/primer-ingreso"
      barraMovil="oculta"
    >
      <PantallaAcceso
        titulo="Crea tu contraseña"
        subtitulo={`Hola, ${usuario.nombre}. Entraste con una contraseña temporal: elige una propia para seguir.`}
        movil="hero"
      >
        <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Crea tu contraseña">
          {falla && <Aviso tipo="error">{falla}</Aviso>}
          <Campo etiqueta="Contraseña temporal" type="password" autoComplete="current-password" value={actual} onChange={(evento) => setActual(evento.target.value)} error={errores.actual} />
          <Campo
            etiqueta="Contraseña nueva"
            type="password"
            autoComplete="new-password"
            value={nueva}
            onChange={(evento) => setNueva(evento.target.value)}
            error={errores.nueva}
            aria-describedby="reglas-primer-ingreso"
          />
          <Campo
            etiqueta="Repite la contraseña nueva"
            type="password"
            autoComplete="new-password"
            value={repetida}
            onChange={(evento) => setRepetida(evento.target.value)}
            error={errores.repetida}
          />
          <ReglasPassword reglas={reglasPassword(nueva, repetida)} id="reglas-primer-ingreso" />
          <Boton type="submit" ancho cargando={enviando}>
            {enviando ? 'Guardando…' : 'Guardar y continuar'}
          </Boton>
          <button
            type="button"
            className={`${e.destacadoAccion} ${e.centrado}`}
            onClick={() => void sesion.logout().then(() => navegar(salida, { replace: true }))}
          >
            Cerrar sesión
          </button>
        </form>
      </PantallaAcceso>
    </MarcoPortal>
  );
}
