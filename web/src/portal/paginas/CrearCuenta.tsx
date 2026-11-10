import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Campo } from '../../formularios/Campo';
import { useCrearCuenta, type CrearCuentaDatos } from '../api';
import { useContextoPortal } from '../contexto';
import { mostrarTelefono } from '../telefono';
import estilos from '../portal.module.css';

type Campos = Omit<CrearCuentaDatos, 'sitio_web'>;
type Errores = Partial<Record<keyof Campos | 'general', string>>;

const ETIQUETAS: Record<keyof Campos, string> = {
  nombre: 'Nombre',
  telefono: 'WhatsApp',
  email: 'Correo',
  password: 'Contraseña',
};

function validar(datos: Campos): Errores {
  const errores: Errores = {};
  for (const campo of Object.keys(ETIQUETAS) as (keyof Campos)[]) {
    if (!datos[campo].trim()) errores[campo] = 'Completa este campo.';
  }
  if (datos.telefono && !/^\+[1-9]\d{7,14}$/.test(datos.telefono.replace(/[\s-]/g, ''))) {
    errores.telefono = 'Incluye el código de país, p. ej. +56 9 1234 5678.';
  }
  if (datos.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(datos.email)) errores.email = 'Ingresa un correo válido.';
  if (datos.password && datos.password.length < 10) errores.password = 'Mínimo 10 caracteres.';
  return errores;
}

/**
 * HU-35: cuenta opcional del pasajero en esta empresa. Queda pendiente hasta responder «CONFIRMAR CUENTA» por
 * WhatsApp. Pedir como invitado sigue disponible en el formulario del portal.
 */
export function CrearCuenta() {
  const { api, empresa, slug } = useContextoPortal();
  const crear = useCrearCuenta(api, slug);
  const [datos, setDatos] = useState<Campos>({ nombre: '', telefono: '', email: '', password: '' });
  const [trampa, setTrampa] = useState('');
  const [errores, setErrores] = useState<Errores>({});
  const [listo, setListo] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados = validar(datos);
    setErrores(encontrados);
    if (Object.keys(encontrados).length) return;
    try {
      await crear.mutateAsync({ ...datos, telefono: datos.telefono.replace(/[\s-]/g, ''), sitio_web: trampa });
      setListo(true);
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const cuerpo = (error.cuerpo ?? {}) as Record<string, string[] | undefined>;
        const delServidor: Errores = {};
        for (const campo of Object.keys(ETIQUETAS) as (keyof Campos)[]) {
          if (cuerpo[campo]?.[0]) delServidor[campo] = cuerpo[campo]![0];
        }
        setErrores(Object.keys(delServidor).length ? delServidor : { general: 'Revisa los datos.' });
      } else if (error instanceof ErrorApi && error.estado === 429) {
        setErrores({ general: 'Demasiados intentos. Espera unos minutos e intenta de nuevo.' });
      } else {
        setErrores({ general: 'No se pudo crear la cuenta. Intenta de nuevo.' });
      }
    }
  }

  if (listo) {
    return (
      <section className={estilos.tarjeta} aria-labelledby="titulo-cuenta">
        <h1 id="titulo-cuenta">Confirma tu cuenta</h1>
        <p className={estilos.destacado}>
          Te enviamos un WhatsApp al <strong>{mostrarTelefono(datos.telefono.replace(/[\s-]/g, ''))}</strong>. Responde{' '}
          <strong>CONFIRMAR CUENTA</strong> en los próximos {empresa.expiracion_verificacion_min} minutos para activarla.
        </p>
        <Link to={`/login?volver=${encodeURIComponent('/mis-reservas')}`}>Iniciar sesión</Link>
      </section>
    );
  }

  return (
    <form className={estilos.tarjeta} onSubmit={(e) => void enviar(e)} noValidate aria-labelledby="titulo-cuenta">
      <h1 id="titulo-cuenta">Crear cuenta</h1>
      <p>
        Con una cuenta en {empresa.razon_social} ves tus viajes y no confirmas tu WhatsApp cada vez. Es opcional: puedes{' '}
        <Link to={`/solicitar/${slug}`}>pedir como invitado</Link>.
      </p>
      {errores.general && (
        <p className={estilos.errorCampo} role="alert">
          {errores.general}
        </p>
      )}
      {(Object.keys(ETIQUETAS) as (keyof Campos)[]).map((campo) => (
        <Campo key={campo} etiqueta={ETIQUETAS[campo]} error={errores[campo]}>
          {(control) => (
            <input
              {...control}
              type={campo === 'password' ? 'password' : campo === 'email' ? 'email' : campo === 'telefono' ? 'tel' : 'text'}
              autoComplete={campo === 'password' ? 'new-password' : campo === 'email' ? 'email' : campo === 'telefono' ? 'tel' : 'name'}
              value={datos[campo]}
              onChange={(e) => setDatos({ ...datos, [campo]: e.target.value })}
            />
          )}
        </Campo>
      ))}
      <div className={estilos.trampa} aria-hidden="true">
        <label>
          Sitio web
          <input type="text" tabIndex={-1} autoComplete="off" value={trampa} onChange={(e) => setTrampa(e.target.value)} />
        </label>
      </div>
      <button type="submit" className={estilos.botonPrincipal} disabled={crear.isPending}>
        {crear.isPending ? 'Enviando…' : 'Crear cuenta'}
      </button>
    </form>
  );
}
