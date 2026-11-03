import { zodResolver } from '@hookform/resolvers/zod';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { hoy } from '../../hora/hora';
import { useCrearConductor } from '../api';
import { erroresDelBackend, mensajeDeError } from '../errores';
import { LICENCIAS } from '../etiquetas';
import { CONDUCTOR_VACIO, esquemaConductorNuevo, type DatosConductorNuevo, type ValoresConductorNuevo } from '../formularios';

const CAMPOS = ['nombre', 'email', 'rut', 'telefono', 'licencia_clase', 'licencia_vence'] as const;

/** Alta del conductor con su cuenta. La contraseña se genera después, desde la ficha. */
export function ConductorNuevo() {
  const crear = useCrearConductor();
  const navegar = useNavigate();
  const esquema = useMemo(() => esquemaConductorNuevo(hoy()), []);
  const [falla, setFalla] = useState<string[]>([]);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ValoresConductorNuevo, unknown, DatosConductorNuevo>({ resolver: zodResolver(esquema), defaultValues: CONDUCTOR_VACIO });

  async function registrar(datos: DatosConductorNuevo) {
    setFalla([]);
    try {
      const conductor = await crear.mutateAsync(datos);
      navegar(`/conductores/${conductor.id}`, {
        replace: true,
        state: { aviso: 'Conductor registrado. Genera su contraseña temporal para que pueda ingresar a la app.' },
      });
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const { campos, generales } = erroresDelBackend(error.cuerpo, CAMPOS);
        const primero = Object.keys(campos)[0];
        for (const [campo, mensaje] of Object.entries(campos)) {
          setError(campo as keyof ValoresConductorNuevo, { message: mensaje }, { shouldFocus: campo === primero });
        }
        setFalla(generales);
      } else {
        setFalla([mensajeDeError(error, 'el conductor')]);
      }
    }
  }

  return (
    <section>
      <h1>Nuevo conductor</h1>
      <form className={estilos.formulario} onSubmit={handleSubmit(registrar)} noValidate>
        {falla.map((mensaje) => (
          <Aviso key={mensaje} tipo="error">
            {mensaje}
          </Aviso>
        ))}
        <fieldset>
          <legend>Datos del conductor</legend>
          <Campo etiqueta="Nombre" error={errors.nombre?.message}>
            {(control) => <input {...control} {...register('nombre')} maxLength={80} autoComplete="off" />}
          </Campo>
          <Campo etiqueta="Correo de acceso" error={errors.email?.message} ayuda="Con este correo ingresa a la app.">
            {(control) => <input {...control} {...register('email')} type="email" autoComplete="off" />}
          </Campo>
          <Campo etiqueta="RUT" error={errors.rut?.message} ayuda="Con guion y dígito verificador: 12.345.678-5.">
            {(control) => <input {...control} {...register('rut')} autoComplete="off" />}
          </Campo>
          <Campo etiqueta="Teléfono" error={errors.telefono?.message} ayuda="Móvil chileno: +569 y 8 dígitos.">
            {(control) => <input {...control} {...register('telefono')} type="tel" inputMode="tel" autoComplete="off" />}
          </Campo>
          <Campo etiqueta="Clase de licencia" error={errors.licencia_clase?.message}>
            {(control) => (
              <select {...control} {...register('licencia_clase')}>
                {Object.entries(LICENCIAS).map(([valor, texto]) => (
                  <option key={valor} value={valor}>
                    {texto}
                  </option>
                ))}
              </select>
            )}
          </Campo>
          <Campo etiqueta="Vencimiento de la licencia" error={errors.licencia_vence?.message}>
            {(control) => <input {...control} {...register('licencia_vence')} type="date" />}
          </Campo>
        </fieldset>
        <div className={estilos.pie}>
          <button type="submit" className={estilos.boton} disabled={isSubmitting}>
            {isSubmitting ? 'Guardando…' : 'Registrar conductor'}
          </button>
          <Link to="/conductores" className={estilos.botonSecundario}>
            Volver
          </Link>
        </div>
      </form>
    </section>
  );
}
