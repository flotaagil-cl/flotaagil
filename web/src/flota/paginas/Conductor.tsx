import { zodResolver } from '@hookform/resolvers/zod';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { formatearFecha, formatearFechaHora, hoy } from '../../hora/hora';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import {
  useAsociarVehiculo,
  useConductor,
  useEditarConductor,
  useQuitarVehiculo,
  useVehiculos,
  type Conductor as TipoConductor,
} from '../api';
import { FallaDeCarga, NoEncontrado } from '../componentes/comunes';
import { erroresDelBackend, mensajeDeError } from '../errores';
import { avisoLicencia, ESTADOS_CONDUCTOR, LICENCIAS } from '../etiquetas';
import { cuerpoEditarConductor, esquemaConductor, type DatosConductor, type ValoresConductor } from '../formularios';

const CAMPOS = ['nombre', 'rut', 'telefono', 'licencia_clase', 'licencia_vence'] as const;

export function Conductor() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontrado que="el conductor" volverA="/conductores" texto="Volver a los conductores" />;
  return <ConductorDe id={id} />;
}

function ConductorDe({ id }: { id: number }) {
  const consulta = useConductor(id);
  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) {
    if (consulta.error instanceof ErrorApi && consulta.error.estado === 404) {
      return <NoEncontrado que="el conductor" volverA="/conductores" texto="Volver a los conductores" />;
    }
    return <FallaDeCarga error={consulta.error} que="el conductor" reintentar={() => void consulta.refetch()} />;
  }
  return <Ficha conductor={consulta.data} />;
}

function datosDe(conductor: TipoConductor): DatosConductor {
  const { nombre, rut, telefono, licencia_clase, licencia_vence } = conductor;
  return { nombre, rut, telefono, licencia_clase, licencia_vence };
}

function Ficha({ conductor }: { conductor: TipoConductor }) {
  const [editando, setEditando] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);
  const alertaLicencia = avisoLicencia(conductor.licencia_vence, hoy());

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>{conductor.nombre}</h1>
        <Link to="/conductores" className={estilos.botonSecundario}>
          Volver a los conductores
        </Link>
      </div>
      {aviso && <Aviso>{aviso}</Aviso>}

      {editando ? (
        <EditarDatos
          conductor={conductor}
          alTerminar={(mensaje) => {
            setEditando(false);
            setAviso(mensaje);
          }}
        />
      ) : (
        <div className={estilos.tarjeta}>
          <h2>Datos</h2>
          <dl className={estilos.datos}>
            <div>
              <dt>RUT</dt>
              <dd>{conductor.rut}</dd>
            </div>
            <div>
              <dt>Teléfono</dt>
              <dd>{conductor.telefono}</dd>
            </div>
            <div>
              <dt>Correo de acceso</dt>
              <dd>{conductor.email}</dd>
            </div>
            <div>
              <dt>Cuenta</dt>
              <dd>{conductor.activo ? 'Habilitada' : 'Deshabilitada'}</dd>
            </div>
            <div>
              <dt>Licencia</dt>
              <dd>
                Clase {LICENCIAS[conductor.licencia_clase]} · vence {formatearFecha(conductor.licencia_vence)}
                {alertaLicencia && <span className={estilos.alerta}>{alertaLicencia}</span>}
              </dd>
            </div>
            <div>
              <dt>Estado</dt>
              <dd>
                {ESTADOS_CONDUCTOR[conductor.estado]}
                {conductor.vehiculo_activo ? ` · declaró ${conductor.vehiculo_activo.patente}` : ''}
              </dd>
            </div>
            <div>
              <dt>Consentimiento de ubicación</dt>
              <dd>
                {conductor.consentimiento_gps_en ? `Aceptado el ${formatearFechaHora(conductor.consentimiento_gps_en)}` : 'Pendiente'}
              </dd>
            </div>
          </dl>
          <div className={estilos.acciones}>
            <button
              type="button"
              className={estilos.boton}
              onClick={() => {
                setAviso(null);
                setEditando(true);
              }}
            >
              Editar datos
            </button>
          </div>
          <p className={estilos.explicacion}>El correo y la contraseña de acceso no se cambian desde aquí.</p>
        </div>
      )}

      <Vehiculos conductor={conductor} />
    </section>
  );
}

function EditarDatos({ conductor, alTerminar }: { conductor: TipoConductor; alTerminar: (mensaje: string) => void }) {
  const editar = useEditarConductor(conductor.id);
  const esquema = useMemo(() => esquemaConductor(hoy()), []);
  const [antes] = useState(() => datosDe(conductor));
  const [falla, setFalla] = useState<string[]>([]);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ValoresConductor, unknown, DatosConductor>({ resolver: zodResolver(esquema), defaultValues: antes });

  async function guardar(datos: DatosConductor) {
    setFalla([]);
    const cambios = cuerpoEditarConductor(datos, antes);
    if (Object.keys(cambios).length === 0) {
      alTerminar('No hay cambios que guardar.');
      return;
    }
    try {
      await editar.mutateAsync(cambios);
      alTerminar('Datos guardados.');
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const { campos, generales } = erroresDelBackend(error.cuerpo, CAMPOS);
        const primero = Object.keys(campos)[0];
        for (const [campo, mensaje] of Object.entries(campos)) {
          setError(campo as keyof ValoresConductor, { message: mensaje }, { shouldFocus: campo === primero });
        }
        setFalla(generales);
      } else {
        setFalla([mensajeDeError(error, 'el conductor')]);
      }
    }
  }

  return (
    <form className={estilos.formulario} onSubmit={handleSubmit(guardar)} noValidate>
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
          {isSubmitting ? 'Guardando…' : 'Guardar datos'}
        </button>
        <button type="button" className={estilos.botonSecundario} disabled={isSubmitting} onClick={() => alTerminar('')}>
          Descartar
        </button>
      </div>
    </form>
  );
}

/** Vehículos asociados (N:M): quitar uno y buscar uno activo para asociarlo. */
function Vehiculos({ conductor }: { conductor: TipoConductor }) {
  const asociar = useAsociarVehiculo(conductor.id);
  const quitar = useQuitarVehiculo(conductor.id);
  const [busqueda, setBusqueda] = useState('');
  const [falla, setFalla] = useState<string | null>(null);
  const candidatos = useVehiculos({ activo: true, ...(busqueda.trim() && { q: busqueda.trim() }) });
  const asociados = new Set(conductor.vehiculos.map((v) => v.id));
  const disponibles = candidatos.data?.results.filter((v) => !asociados.has(v.id)) ?? [];
  const ocupado = asociar.isPending || quitar.isPending;

  async function hacer(accion: () => Promise<unknown>) {
    setFalla(null);
    try {
      await accion();
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        setFalla(erroresDelBackend(error.cuerpo, []).generales.join(' '));
      } else {
        setFalla(mensajeDeError(error, 'el conductor'));
      }
    }
  }

  return (
    <div className={estilos.tarjeta}>
      <h2>Vehículos</h2>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {conductor.vehiculos.length ? (
        <ul className={estilos.listaAcciones} aria-label="Vehículos asociados">
          {conductor.vehiculos.map((vehiculo) => (
            <li key={vehiculo.id}>
              <span>
                <Link to={`/vehiculos/${vehiculo.id}`}>{vehiculo.patente}</Link> · {vehiculo.marca_modelo}
                <span className={estilos.secundario}>
                  Desde {formatearFecha(vehiculo.desde)}
                  {vehiculo.activo ? '' : ' · inactivo'}
                  {conductor.vehiculo_activo?.id === vehiculo.id ? ' · declarado para el turno' : ''}
                </span>
              </span>
              <button
                type="button"
                className={estilos.botonSecundario}
                disabled={ocupado}
                aria-label={`Quitar ${vehiculo.patente}`}
                onClick={() => void hacer(() => quitar.mutateAsync(vehiculo.id))}
              >
                Quitar
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p>Sin vehículos asociados: no podrá quedar Disponible hasta tener uno.</p>
      )}

      <h3>Asociar un vehículo</h3>
      <label className={estilos.busqueda}>
        Buscar vehículo activo
        <input type="search" placeholder="Patente o marca y modelo" value={busqueda} onChange={(e) => setBusqueda(e.target.value)} />
      </label>
      {candidatos.isError ? (
        <p role="alert">{mensajeDeError(candidatos.error, 'la página')}</p>
      ) : candidatos.isPending ? (
        <p>Buscando…</p>
      ) : disponibles.length === 0 ? (
        <p>No hay vehículos activos sin asociar{busqueda.trim() ? ' que coincidan' : ''}.</p>
      ) : (
        <ul className={estilos.listaAcciones} aria-label="Vehículos para asociar">
          {disponibles.map((vehiculo) => (
            <li key={vehiculo.id}>
              <span>
                {vehiculo.patente} · {vehiculo.marca_modelo}
              </span>
              <button
                type="button"
                className={estilos.boton}
                disabled={ocupado}
                aria-label={`Asociar ${vehiculo.patente}`}
                onClick={() => void hacer(() => asociar.mutateAsync(vehiculo.id))}
              >
                Asociar
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
