import { zodResolver } from '@hookform/resolvers/zod';
import { useState, type ReactNode } from 'react';
import { useForm } from 'react-hook-form';
import { Navigate, useSearchParams } from 'react-router';
import { z } from 'zod';
import { Cargando } from '../componentes/Cargando';
import { SinConexion } from '../componentes/SinConexion';
import { useRutas } from '../rutas/contexto';
import { inicioDeRol } from '../rutas/tabla';
import { destinoSeguro } from '../rutas/volver';
import { useIniciarSesion, useSesion } from '../sesion/SesionProvider';

const esquema = z.object({
  email: z.email({ error: 'Ingresa un correo válido.' }),
  password: z.string().min(1, { error: 'Ingresa tu contraseña.' }),
});

export type DatosIngreso = z.infer<typeof esquema>;

/**
 * Lógica del inicio de sesión único (HU-33), compartida por el ingreso del panel (/login) y el del portal
 * (/solicitar/:slug/ingresar): aceptan todos los roles y cada uno llega a su vista con `inicioDeRol`.
 * `bloqueo` es lo que se muestra en vez del formulario (cargando, sin conexión o la redirección).
 */
export function useIngreso() {
  const estado = useIniciarSesion();
  const { sesion } = useSesion();
  const rutas = useRutas();
  const [parametros] = useSearchParams();
  const [error, setError] = useState<string | null>(null);
  const formulario = useForm<DatosIngreso>({ resolver: zodResolver(esquema) });

  let bloqueo: ReactNode = null;
  // No se muestra el formulario hasta saber si ya hay sesión (refresh silencioso).
  if (estado.fase === 'inicial' || estado.fase === 'cargando') bloqueo = <Cargando />;
  else if (estado.fase === 'sin_conexion') {
    bloqueo = <SinConexion motivo={estado.motivo} alReintentar={() => void sesion.reintentar()} />;
  } else if (estado.fase === 'autenticada') {
    // HU-33: sin `volver`, cada rol llega a su vista.
    const destino = parametros.get('volver')
      ? destinoSeguro(parametros.get('volver'), rutas, window.location.origin)
      : inicioDeRol(estado.usuario.rol);
    bloqueo = <Navigate to={destino} replace />;
  }

  const enviar = formulario.handleSubmit(async (datos: DatosIngreso) => {
    setError(null);
    sesion.descartarAviso();
    const respuesta = await sesion.login(datos.email, datos.password);
    if (!respuesta.ok) setError(respuesta.mensaje);
  });

  return { bloqueo, aviso: 'aviso' in estado ? estado.aviso : undefined, error, formulario, enviar };
}
