import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Campo } from '../../formularios/Campo';
import { useRegistrarEmpresa, type RegistroEmpresa as Datos } from '../api';
import { useContextoPortal } from '../contexto';
import estilos from '../portal.module.css';

type Campos = Omit<Datos, 'sitio_web'>;
type Errores = Partial<Record<keyof Campos | 'general', string>>;

const VACIO: Campos = {
  cliente_nombre: '',
  cliente_rut: '',
  direccion: '',
  encargado_nombre: '',
  email: '',
  encargado_telefono: '',
  password: '',
};

const ETIQUETAS: Record<keyof Campos, string> = {
  cliente_nombre: 'Razón social',
  cliente_rut: 'RUT de la empresa',
  direccion: 'Dirección',
  encargado_nombre: 'Nombre del encargado',
  email: 'Correo del encargado',
  encargado_telefono: 'Teléfono del encargado',
  password: 'Contraseña',
};

function validar(datos: Campos): Errores {
  const errores: Errores = {};
  for (const campo of Object.keys(ETIQUETAS) as (keyof Campos)[]) {
    if (!datos[campo].trim()) errores[campo] = 'Completa este campo.';
  }
  if (datos.email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(datos.email)) errores.email = 'Ingresa un correo válido.';
  if (datos.encargado_telefono && !/^\+[1-9]\d{7,14}$/.test(datos.encargado_telefono.replace(/\s/g, ''))) {
    errores.encargado_telefono = 'Formato internacional, p. ej. +56912345678.';
  }
  if (datos.password && datos.password.length < 10) errores.password = 'Mínimo 10 caracteres.';
  return errores;
}

/**
 * HU-34: la empresa cliente se registra y queda en revisión hasta que la empresa de taxis la apruebe. Página
 * pública del portal: sin sesión, con el mismo campo trampa que el formulario de viajes.
 */
export function RegistroEmpresa() {
  const { api, empresa, slug } = useContextoPortal();
  const registrar = useRegistrarEmpresa(api, slug);
  const [datos, setDatos] = useState<Campos>(VACIO);
  const [trampa, setTrampa] = useState('');
  const [errores, setErrores] = useState<Errores>({});
  const [listo, setListo] = useState(false);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados = validar(datos);
    setErrores(encontrados);
    if (Object.keys(encontrados).length) return;
    try {
      await registrar.mutateAsync({
        ...datos,
        encargado_telefono: datos.encargado_telefono.replace(/\s/g, ''),
        sitio_web: trampa,
      });
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
        setErrores({ general: 'No se pudo enviar el registro. Intenta de nuevo.' });
      }
    }
  }

  if (listo) {
    return (
      <section className={estilos.tarjeta} aria-labelledby="titulo-registro">
        <h1 id="titulo-registro">Registro recibido</h1>
        <p>
          {empresa.razon_social} revisará los datos de {datos.cliente_nombre}. Te avisaremos a {datos.email} cuando se
          apruebe. Mientras tanto puedes iniciar sesión para ver el estado.
        </p>
        <Link to={`/login?volver=${encodeURIComponent('/mi-convenio')}`}>Iniciar sesión</Link>
      </section>
    );
  }

  return (
    <form className={estilos.tarjeta} onSubmit={(e) => void enviar(e)} noValidate aria-labelledby="titulo-registro">
      <h1 id="titulo-registro">Registrar mi empresa</h1>
      <p>
        Para pedir viajes a nombre de tu empresa con {empresa.razon_social}. El registro queda en revisión hasta que lo
        aprueben.
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
              type={campo === 'password' ? 'password' : campo === 'email' ? 'email' : campo === 'encargado_telefono' ? 'tel' : 'text'}
              autoComplete={campo === 'password' ? 'new-password' : campo === 'email' ? 'email' : 'off'}
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
      <button type="submit" className={estilos.botonPrincipal} disabled={registrar.isPending}>
        {registrar.isPending ? 'Enviando…' : 'Registrar empresa'}
      </button>
    </form>
  );
}
