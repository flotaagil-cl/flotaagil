import { zodResolver } from '@hookform/resolvers/zod';
import { useMemo, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useLocation } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import type { NombreIcono } from '../../diseno/iconos';
import { Campo } from '../../formularios/Campo';
import { formatearFecha, formatearFechaHora, hoy } from '../../hora/hora';
import { ContactoPasajero } from '../../reservas/componentes/ContactoPasajero';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import {
  useAsociarVehiculo,
  useConductor,
  useEditarConductor,
  useQuitarVehiculo,
  useVehiculos,
  type Conductor as TipoConductor,
  type EstadoConductor,
} from '../api';
import { FallaDeCarga, NoEncontrado } from '../componentes/comunes';
import { CuentaConductor } from '../componentes/CuentaConductor';
import { TerminarTurno } from '../componentes/TerminarTurno';
import { erroresDelBackend, mensajeDeError } from '../errores';
import { useEstadoEnVivo } from '../estadoEnVivo';
import { ACCESOS_APP, avisoLicencia, ESTADOS_CONDUCTOR, LICENCIAS } from '../etiquetas';
import s from '../flota.module.css';
import { cuerpoEditarConductor, esquemaConductor, type DatosConductor, type ValoresConductor } from '../formularios';

const CAMPOS = ['nombre', 'rut', 'telefono', 'licencia_clase', 'licencia_vence'] as const;

type Tono = 'ok' | 'info' | 'revision' | 'peligro' | 'neutro';

const ESTILO_ESTADO: Record<EstadoConductor, { tono: Tono; icono: NombreIcono }> = {
  DISPONIBLE: { tono: 'ok', icono: 'check' },
  EN_VIAJE: { tono: 'info', icono: 'auto' },
  NO_DISPONIBLE: { tono: 'neutro', icono: 'menos' },
};

const ESTILO_ACCESO: Record<keyof typeof ACCESOS_APP, { tono: Tono; icono: NombreIcono }> = {
  ACTIVA: { tono: 'ok', icono: 'llave' },
  TEMPORAL: { tono: 'revision', icono: 'reloj' },
  TEMPORAL_VENCIDA: { tono: 'peligro', icono: 'alerta' },
  SIN_PASSWORD: { tono: 'peligro', icono: 'candado' },
  DESHABILITADA: { tono: 'neutro', icono: 'cerrar' },
};

export function Conductor() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontrado que="el conductor" volverA="/conductores" texto="Volver a los conductores" />;
  return <ConductorDe id={id} />;
}

function ConductorDe({ id }: { id: number }) {
  const consulta = useConductor(id);
  useEstadoEnVivo();
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
  const ubicacion = useLocation();
  const [aviso, setAviso] = useState<string | null>((ubicacion.state as { aviso?: string } | null)?.aviso ?? null);
  const alertaLicencia = avisoLicencia(conductor.licencia_vence, hoy());
  const claveAcceso = conductor.activo ? conductor.acceso : 'DESHABILITADA';
  const estiloEstado = ESTILO_ESTADO[conductor.estado];
  const estiloAcceso = ESTILO_ACCESO[claveAcceso];

  return (
    <section>
      <div className={s.encabezado}>
        <div className={s.tituloBloque}>
          <h1>{conductor.nombre}</h1>
          <div className={s.metaFicha}>
            <span className={s.badge} data-tono={estiloAcceso.tono}>
              <Icono nombre={estiloAcceso.icono} tamano={13} />
              {ACCESOS_APP[claveAcceso]}
            </span>
            <span className={s.metaTexto}>
              Licencia clase {LICENCIAS[conductor.licencia_clase]} ·{' '}
              {conductor.vehiculos.length === 1 ? '1 vehículo asociado' : `${conductor.vehiculos.length} vehículos asociados`}
            </span>
          </div>
        </div>
        <div className={s.accionesEncabezado}>
          <Link to="/conductores" className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
            <Icono nombre="atras" tamano={16} />
            Volver a los conductores
          </Link>
        </div>
      </div>

      {aviso && <Aviso>{aviso}</Aviso>}

      <div className={s.cuadriculaFicha}>
        <div className={s.columnaPrincipal}>
          {editando ? (
            <EditarDatos
              conductor={conductor}
              alTerminar={(mensaje) => {
                setEditando(false);
                setAviso(mensaje);
              }}
            />
          ) : (
            <div className={s.tarjeta}>
              <div className={s.cabeceraTarjeta}>
                <h2>Datos</h2>
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
              <dl className={s.datosGrid}>
                <div className={s.datoItem}>
                  <dt>RUT</dt>
                  <dd className={s.tabular}>{conductor.rut}</dd>
                </div>
                <div className={s.datoItem}>
                  <dt>Teléfono</dt>
                  <dd>
                    <ContactoPasajero telefono={conductor.telefono} compacto nombre={conductor.nombre} />
                  </dd>
                </div>
                <div className={s.datoItem}>
                  <dt>Licencia</dt>
                  <dd>
                    <span>
                      Clase {LICENCIAS[conductor.licencia_clase]} · vence {formatearFecha(conductor.licencia_vence)}
                    </span>
                    {alertaLicencia && (
                      <div>
                        <span className={s.badgeLicencia} data-tono={alertaLicencia === 'Licencia vencida' ? 'peligro' : 'revision'}>
                          <Icono nombre="alerta" tamano={12} />
                          {alertaLicencia}
                        </span>
                      </div>
                    )}
                  </dd>
                </div>
                <div className={s.datoItem}>
                  <dt>Estado</dt>
                  <dd>
                    {/* Texto continuo requerido por turno.test.tsx («Disponible · declaró BCDF10»). */}
                    <span className={s.badge} data-tono={estiloEstado.tono}>
                      <Icono nombre={estiloEstado.icono} tamano={13} />
                      {ESTADOS_CONDUCTOR[conductor.estado]}
                      {conductor.vehiculo_activo ? ` · declaró ${conductor.vehiculo_activo.patente}` : ''}
                    </span>
                  </dd>
                </div>
                <div className={s.datoItem}>
                  <dt>Consentimiento de ubicación</dt>
                  <dd>
                    {conductor.consentimiento_gps_en ? `Aceptado el ${formatearFechaHora(conductor.consentimiento_gps_en)}` : 'Pendiente'}
                  </dd>
                </div>
              </dl>
              <p className={estilos.explicacion}>El correo de acceso se cambia en «Acceso a la app».</p>
            </div>
          )}

          <Vehiculos conductor={conductor} />
        </div>

        <aside className={s.columnaLateral}>
          <CuentaConductor conductor={conductor} />
          <TerminarTurno conductor={conductor} />
        </aside>
      </div>
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
    <form className={s.formularioTarjeta} onSubmit={handleSubmit(guardar)} noValidate>
      {falla.map((mensaje) => (
        <Aviso key={mensaje} tipo="error">
          {mensaje}
        </Aviso>
      ))}
      <fieldset className={s.fieldsetLimpio}>
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
      <div className={s.pieFormulario}>
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
    <div className={s.tarjeta}>
      <div className={s.cabeceraTarjeta}>
        <h2>Vehículos</h2>
        {conductor.vehiculos.length > 0 && (
          <span className={s.badge} data-tono="neutro">
            {conductor.vehiculos.length} {conductor.vehiculos.length === 1 ? 'asociado' : 'asociados'}
          </span>
        )}
      </div>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {conductor.vehiculos.length ? (
        <ul className={s.listaAsociados} aria-label="Vehículos asociados">
          {conductor.vehiculos.map((vehiculo) => (
            <li key={vehiculo.id}>
              <span>
                <Link to={`/vehiculos/${vehiculo.id}`} className={s.patente}>
                  {vehiculo.patente}
                </Link>{' '}
                <span>· {vehiculo.marca_modelo}</span>
                <span className={s.secundario}>
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
        <p className={s.notaEstado}>Sin vehículos asociados: no podrá quedar Disponible hasta tener uno.</p>
      )}

      <div className={s.seccionAsociar}>
        <h3>Asociar un vehículo</h3>
        <label className={s.campoFiltro}>
          Buscar vehículo activo
          <input
            type="search"
            className={s.control}
            placeholder="Patente o marca y modelo"
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
          />
        </label>
        {candidatos.isError ? (
          <p role="alert">{mensajeDeError(candidatos.error, 'la página')}</p>
        ) : candidatos.isPending ? (
          <p className={s.secundario}>Buscando…</p>
        ) : disponibles.length === 0 ? (
          <p className={s.secundario}>No hay vehículos activos sin asociar{busqueda.trim() ? ' que coincidan' : ''}.</p>
        ) : (
          <ul className={s.listaCandidatos} aria-label="Vehículos para asociar">
            {disponibles.map((vehiculo) => (
              <li key={vehiculo.id}>
                <span>
                  <span className={s.patente}>{vehiculo.patente}</span> · {vehiculo.marca_modelo}
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
    </div>
  );
}
