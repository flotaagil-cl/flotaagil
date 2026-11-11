import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Boton } from '../../diseno/Boton';
import { Campo, Casilla } from '../../diseno/Campo';
import e from '../../diseno/diseno.module.css';
import { PantallaAcceso } from '../../diseno/PantallaAcceso';
import { Destacado } from '../../diseno/Tarjeta';
import { useCrearCuenta } from '../api';
import { useContextoPortal } from '../contexto';
import { mostrarTelefono, normalizarWhatsapp } from '../telefono';

interface Campos {
  nombre: string;
  apellido: string;
  email: string;
  telefono: string;
  password: string;
}
type Errores = Partial<Record<keyof Campos | 'privacidad' | 'general', string>>;

const MINIMO = 10;

function validar(datos: Campos, privacidad: boolean): Errores {
  const errores: Errores = {};
  for (const campo of Object.keys(datos) as (keyof Campos)[]) {
    if (!datos[campo].trim()) errores[campo] = 'Completa este campo.';
  }
  if (datos.telefono.trim() && !/^\+[1-9]\d{7,14}$/.test(normalizarWhatsapp(datos.telefono))) {
    errores.telefono = 'Revisa el número: 9 dígitos si es de Chile, o con + y el código si es de otro país.';
  }
  if (datos.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(datos.email.trim())) errores.email = 'Ingresa un correo válido.';
  if (datos.password && datos.password.length < MINIMO) errores.password = `Mínimo ${MINIMO} caracteres.`;
  if (!privacidad) errores.privacidad = 'Para crear la cuenta debes aceptar el aviso de privacidad.';
  return errores;
}

/**
 * HU-35 con el diseño de HU-38: cuenta del pasajero en esta empresa. Queda pendiente hasta responder
 * «CONFIRMAR CUENTA» por WhatsApp. Mismo endpoint de HU-35; nombre y apellido viajan juntos en `nombre`.
 */
export function CrearCuenta() {
  const { api, empresa, slug } = useContextoPortal();
  const crear = useCrearCuenta(api, slug);
  const [datos, setDatos] = useState<Campos>({ nombre: '', apellido: '', email: '', telefono: '', password: '' });
  const [privacidad, setPrivacidad] = useState(false);
  const [trampa, setTrampa] = useState('');
  const [errores, setErrores] = useState<Errores>({});
  const [enviado, setEnviado] = useState<string | null>(null);
  const ingresar = `/login?empresa=${slug}`;

  const cambiar = (campo: keyof Campos) => (evento: { target: { value: string } }) => setDatos({ ...datos, [campo]: evento.target.value });

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados = validar(datos, privacidad);
    setErrores(encontrados);
    if (Object.keys(encontrados).length) return;
    const telefono = normalizarWhatsapp(datos.telefono);
    try {
      await crear.mutateAsync({
        nombre: `${datos.nombre.trim()} ${datos.apellido.trim()}`,
        email: datos.email.trim(),
        telefono,
        password: datos.password,
        sitio_web: trampa,
      });
      setEnviado(telefono);
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const cuerpo = (error.cuerpo ?? {}) as Record<string, string[] | undefined>;
        const delServidor: Errores = {};
        for (const campo of ['nombre', 'email', 'telefono', 'password'] as const) {
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

  if (enviado) {
    return (
      <PantallaAcceso titulo="Confirma tu cuenta" subtitulo="Falta un paso para empezar a pedir." movil="hero" volver={{ a: ingresar, texto: 'Volver a ingresar' }}>
        <Destacado titulo="Revisa tu WhatsApp" icono="mensaje">
          Te enviamos un mensaje al {mostrarTelefono(enviado)}. Responde CONFIRMAR CUENTA en los próximos {empresa.expiracion_verificacion_min} minutos
          para activarla.
        </Destacado>
        <Link to={ingresar} className={`${e.enlace} ${e.centrado}`}>
          Ir a ingresar
        </Link>
      </PantallaAcceso>
    );
  }

  return (
    <PantallaAcceso
      titulo="Crea tu cuenta"
      subtitulo="La necesitas para pedir traslados. Toma menos de un minuto."
      movil="hero"
      volver={{ a: ingresar, texto: 'Volver a ingresar' }}
    >
      <form className={e.formulario} onSubmit={(evento) => void enviar(evento)} noValidate aria-label="Crea tu cuenta">
        {errores.general && (
          <p className={e.alerta} role="alert">
            {errores.general}
          </p>
        )}
        <div className={e.fila}>
          <Campo etiqueta="Nombre" autoComplete="given-name" value={datos.nombre} onChange={cambiar('nombre')} error={errores.nombre} />
          <Campo etiqueta="Apellido" autoComplete="family-name" value={datos.apellido} onChange={cambiar('apellido')} error={errores.apellido} />
        </div>
        <Campo
          etiqueta="Correo"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder="nombre@correo.cl"
          value={datos.email}
          onChange={cambiar('email')}
          error={errores.email}
        />
        <Campo
          etiqueta="WhatsApp"
          type="tel"
          autoComplete="tel-national"
          prefijo="+56"
          placeholder="9 1234 5678"
          ayuda="Número de Chile; si es de otro país, escríbelo con + y su código."
          value={datos.telefono}
          onChange={cambiar('telefono')}
          error={errores.telefono}
        />
        <Campo
          etiqueta="Contraseña"
          type="password"
          autoComplete="new-password"
          placeholder={`Mínimo ${MINIMO} caracteres`}
          value={datos.password}
          onChange={cambiar('password')}
          error={errores.password}
        />
        <Casilla checked={privacidad} onChange={(evento) => setPrivacidad(evento.target.checked)} error={errores.privacidad}>
          Acepto el <Link to={`/solicitar/${slug}/privacidad`}>aviso de privacidad</Link> de {empresa.razon_social}.
        </Casilla>
        <Destacado titulo="Te llegará un WhatsApp para activar tu cuenta" icono="mensaje">
          Responde CONFIRMAR CUENTA.
        </Destacado>
        <div className="solo-lector" aria-hidden="true">
          <label>
            Sitio web
            <input type="text" tabIndex={-1} autoComplete="off" value={trampa} onChange={(evento) => setTrampa(evento.target.value)} />
          </label>
        </div>
        <Boton type="submit" ancho cargando={crear.isPending}>
          {crear.isPending ? 'Enviando…' : 'Crear cuenta'}
        </Boton>
        <p className={e.nota}>
          ¿Ya tienes cuenta?{' '}
          <Link to={ingresar} className={e.enlace}>
            Ingresar
          </Link>
        </p>
      </form>
    </PantallaAcceso>
  );
}
