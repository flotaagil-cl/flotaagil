import { zodResolver } from '@hookform/resolvers/zod';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { hoy } from '../../hora/hora';
import { erroresDelBackend, mensajeDeError } from '../errores';
import { esquemaVehiculo, type DatosVehiculo, type ValoresVehiculo } from '../formularios';

const CAMPOS = ['patente', 'marca_modelo', 'anio', 'capacidad'] as const;

interface Props {
  modo: 'crear' | 'editar';
  iniciales: ValoresVehiculo;
  volverA: string;
  enviar: (datos: DatosVehiculo) => Promise<void>;
}

/** Alta y edición de un vehículo. Al editar, la patente se muestra pero no se cambia. */
export function FormularioVehiculo({ modo, iniciales, volverA, enviar }: Props) {
  const esquema = useMemo(() => esquemaVehiculo(Number(hoy().slice(0, 4))), []);
  const [falla, setFalla] = useState<string[]>([]);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ValoresVehiculo, unknown, DatosVehiculo>({ resolver: zodResolver(esquema), defaultValues: iniciales });

  async function alEnviar(datos: DatosVehiculo) {
    setFalla([]);
    try {
      await enviar(datos);
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const { campos, generales } = erroresDelBackend(error.cuerpo, CAMPOS);
        const primero = Object.keys(campos)[0];
        for (const [campo, mensaje] of Object.entries(campos)) {
          setError(campo as keyof ValoresVehiculo, { message: mensaje }, { shouldFocus: campo === primero });
        }
        setFalla(generales);
      } else {
        setFalla([mensajeDeError(error, 'el vehículo')]);
      }
    }
  }

  return (
    <form className={estilos.formulario} onSubmit={handleSubmit(alEnviar)} noValidate>
      {falla.map((mensaje) => (
        <Aviso key={mensaje} tipo="error">
          {mensaje}
        </Aviso>
      ))}
      <fieldset>
        <legend>Vehículo</legend>
        <Campo etiqueta="Patente" error={errors.patente?.message} ayuda={modo === 'editar' ? 'No se cambia: otra patente es otro vehículo.' : 'AB1234 o ABCD12.'}>
          {(control) => (
            <input {...control} {...register('patente')} autoComplete="off" readOnly={modo === 'editar'} autoCapitalize="characters" />
          )}
        </Campo>
        <Campo etiqueta="Marca y modelo" error={errors.marca_modelo?.message}>
          {(control) => <input {...control} {...register('marca_modelo')} maxLength={60} />}
        </Campo>
        <Campo etiqueta="Año" error={errors.anio?.message}>
          {(control) => <input {...control} {...register('anio')} inputMode="numeric" maxLength={4} />}
        </Campo>
        <Campo etiqueta="Capacidad (pasajeros)" error={errors.capacidad?.message} ayuda="Entre 1 y 7.">
          {(control) => <input {...control} {...register('capacidad')} inputMode="numeric" maxLength={1} />}
        </Campo>
      </fieldset>
      <div className={estilos.pie}>
        <button type="submit" className={estilos.boton} disabled={isSubmitting}>
          {isSubmitting ? 'Guardando…' : modo === 'crear' ? 'Registrar vehículo' : 'Guardar cambios'}
        </button>
        <Link to={volverA} className={estilos.botonSecundario}>
          Volver
        </Link>
      </div>
    </form>
  );
}
