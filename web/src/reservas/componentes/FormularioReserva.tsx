import { zodResolver } from '@hookform/resolvers/zod';
import { useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { Controller, useForm, useWatch, type FieldPath } from 'react-hook-form';
import { Link } from 'react-router';
import { Aviso } from '../../componentes/Aviso';
import { ErrorApi } from '../../api/resultado';
import type { ViajeDetalle } from '../api';
import { erroresDelBackend } from '../errores';
import { CANALES, SENTIDOS } from '../etiquetas';
import {
  CAMPOS_DEL_MODO,
  CANALES_PANEL,
  completarTelefono,
  esquemaReserva,
  SENTIDOS_FORMULARIO,
  type Modificados,
  type Modo,
  type ValoresReserva,
} from '../formulario';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { CampoFechaHora } from '../../formularios/CampoFechaHora';
import { CampoDireccionFormulario } from '../../direcciones/CampoDireccionFormulario';
import type { TipoDeViaje } from '../../diseno/mapa/direcciones';
import { MapaDirecciones } from '../../diseno/mapa/MapaDirecciones';
import { buscarConSesion } from '../../direcciones/sugerencias';
import { useApi } from '../../sesion/SesionProvider';
import s from './FormularioReserva.module.css';

const AEROPUERTO_DIRECCION = 'Aeropuerto de Santiago (SCL)';
/** Coordenadas oficiales de SCL usadas también por el geocodificador del backend. */
const AEROPUERTO_COORDENADAS = { lat: -33.393, lon: -70.7858 };
type SentidoFormulario = (typeof SENTIDOS_FORMULARIO)[number];

function tipoDeMapa(sentido: ValoresReserva['sentido']): TipoDeViaje {
  if (sentido === 'DESDE_AEROPUERTO') return 'desde-aeropuerto';
  return sentido === 'HACIA_AEROPUERTO' ? 'al-aeropuerto' : 'en-la-ciudad';
}

function puntoGuardado(ubicacion: ViajeDetalle['origen'] | undefined, texto: string) {
  return ubicacion && ubicacion.direccion === texto ? { lat: ubicacion.lat, lon: ubicacion.lon } : null;
}

interface Props {
  modo: Modo;
  iniciales: ValoresReserva;
  /** Al editar: la reserva (pasajero y canal en solo lectura, vuelo registrado). */
  viaje?: ViajeDetalle;
  /** Envía a la API; si falla, lanza el error (un 400 se muestra en cada campo). */
  enviar: (valores: ValoresReserva, modificados: Modificados) => Promise<void>;
  /** Mensaje para un error que no es un 400 (red, 409, 500…). */
  describirFalla: (error: unknown) => ReactNode;
  /** Deshabilita el formulario (p. ej. tras un 409) con este aviso. */
  bloqueo?: ReactNode;
  volverA: string;
}

export function FormularioReserva({ modo, iniciales, viaje, enviar, describirFalla, bloqueo, volverA }: Props) {
  const [falla, setFalla] = useState<ReactNode>(null);
  const [generales, setGenerales] = useState<string[]>([]);
  // HU-71: sugerencias con la sesión del panel (zona de la empresa y límite por usuario).
  const api = useApi();
  const buscar = useMemo(() => buscarConSesion((q, signal) => api.GET('/api/direcciones/sugerir/', { params: { query: { q } }, signal })), [api]);
  const {
    register,
    control,
    handleSubmit,
    getValues,
    setValue,
    setError,
    formState: { errors, isSubmitting, dirtyFields, isDirty },
  } = useForm<ValoresReserva>({ resolver: zodResolver(esquemaReserva(modo)), defaultValues: iniciales });
  const sentido = useWatch({ control, name: 'sentido' });
  // HU-71: el mapa muestra el punto elegido. Al editar, el guardado sigue a la vista mientras no cambie el texto.
  const [origenDir, destinoDir, origenElegido, destinoElegido] = useWatch({
    control,
    name: ['origen_dir', 'destino_dir', 'origen_coordenadas', 'destino_coordenadas'],
  });
  const puntoOrigen = origenElegido ?? puntoGuardado(viaje?.origen, origenDir);
  const puntoDestino = destinoElegido ?? puntoGuardado(viaje?.destino, destinoDir);

  function completar() {
    const telefono = getValues('pasajero.telefono');
    const completo = completarTelefono(telefono);
    if (completo !== telefono) setValue('pasajero.telefono', completo, { shouldDirty: true });
  }

  function actualizarDireccionAeropuerto(
    campoTexto: 'origen_dir' | 'destino_dir',
    campoCoords: 'origen_coordenadas' | 'destino_coordenadas',
    debeLlenar: boolean,
  ) {
    const actual = getValues(campoTexto);
    if (debeLlenar) {
      if (!actual.trim() || actual === AEROPUERTO_DIRECCION) {
        setValue(campoTexto, AEROPUERTO_DIRECCION, {
          shouldDirty: true,
          shouldValidate: Boolean(errors[campoTexto]),
        });
        setValue(campoCoords, AEROPUERTO_COORDENADAS, { shouldDirty: true });
      }
      return;
    }
    if (actual === AEROPUERTO_DIRECCION) {
      setValue(campoTexto, '', {
        shouldDirty: true,
        shouldValidate: Boolean(errors[campoTexto]),
      });
      setValue(campoCoords, null, { shouldDirty: true });
    }
  }

  function alCambiarSentido(nuevo: SentidoFormulario) {
    if (modo !== 'crear') return;
    actualizarDireccionAeropuerto('origen_dir', 'origen_coordenadas', nuevo === 'DESDE_AEROPUERTO');
    actualizarDireccionAeropuerto('destino_dir', 'destino_coordenadas', nuevo === 'HACIA_AEROPUERTO');
  }

  async function alEnviar(valores: ValoresReserva) {
    setFalla(null);
    setGenerales([]);
    if (modo === 'editar' && !isDirty) {
      setFalla('No hay cambios que guardar.');
      return;
    }
    try {
      await enviar(valores, dirtyFields as Modificados);
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const { campos, generales: otros } = erroresDelBackend(error.cuerpo, CAMPOS_DEL_MODO[modo]);
        Object.entries(campos).forEach(([campo, mensaje], indice) =>
          setError(campo as FieldPath<ValoresReserva>, { type: 'servidor', message: mensaje }, { shouldFocus: indice === 0 }),
        );
        setGenerales(otros);
      } else {
        setFalla(describirFalla(error));
      }
    }
  }

  function alEnviarFormulario(evento: FormEvent<HTMLFormElement>) {
    // El teléfono se completa a la vista antes de validar.
    if (modo === 'crear') completar();
    void handleSubmit(alEnviar)(evento);
  }

  // Mientras se envía solo se desactiva el botón: los campos siguen enfocables para mostrar los errores.
  const bloqueado = Boolean(bloqueo);

  return (
    <form className={s.formulario} onSubmit={alEnviarFormulario} noValidate>
      {bloqueo && <Aviso tipo="error">{bloqueo}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {generales.map((mensaje) => (
        <Aviso key={mensaje} tipo="error">
          {mensaje}
        </Aviso>
      ))}

      <fieldset className={s.seccion} disabled={bloqueado}>
        <legend className={s.leyenda}>Pasajero</legend>
        {modo === 'crear' ? (
          <div className={s.gridCampos}>
            <Campo etiqueta="Nombre" error={errors.pasajero?.nombre?.message}>
              {(control) => <input autoComplete="off" {...control} {...register('pasajero.nombre')} />}
            </Campo>
            <Campo
              etiqueta="Teléfono (WhatsApp)"
              error={errors.pasajero?.telefono?.message}
              ayuda="Formato +56912345678. Un móvil de 9 dígitos se completa con +56."
            >
              {(control) => (
                <input
                  type="tel"
                  inputMode="tel"
                  autoComplete="off"
                  {...control}
                  {...register('pasajero.telefono', { onBlur: completar })}
                />
              )}
            </Campo>
            <fieldset className={`${s.grupoOpciones} ${s.ancho}`}>
              <legend className={s.leyendaOpciones}>Canal</legend>
              <div className={s.pastillas}>
                {CANALES_PANEL.map((canal) => (
                  <label key={canal} className={s.pastilla}>
                    <input type="radio" className={s.radioOculto} value={canal} {...register('canal')} />
                    {CANALES[canal]}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
        ) : (
          viaje && (
            <div className={s.ancho}>
              <dl className={s.soloLectura}>
                <div>
                  <dt>Nombre</dt>
                  <dd>{viaje.pasajero.nombre}</dd>
                </div>
                <div>
                  <dt>Teléfono</dt>
                  <dd>{viaje.pasajero.telefono ?? 'Sin teléfono'}</dd>
                </div>
                <div>
                  <dt>Canal</dt>
                  <dd>{CANALES[viaje.canal]}</dd>
                </div>
              </dl>
              <p className={s.notaSoloLectura}>El pasajero, su teléfono y el canal no se pueden cambiar al editar.</p>
            </div>
          )
        )}
      </fieldset>

      <fieldset className={s.seccion} disabled={bloqueado}>
        <legend className={s.leyenda}>Trayecto</legend>
        <div className={s.gridCampos}>
          <fieldset className={`${s.grupoOpciones} ${s.ancho}`}>
            <legend className={s.leyendaOpciones}>Sentido</legend>
            <div className={s.pastillas}>
              {SENTIDOS_FORMULARIO.map((valor) => (
                <label key={valor} className={s.pastilla}>
                  <input
                    type="radio"
                    className={s.radioOculto}
                    value={valor}
                    {...register('sentido', {
                      onChange: (evento) => alCambiarSentido(evento.target.value as SentidoFormulario),
                    })}
                  />
                  {SENTIDOS[valor]}
                </label>
              ))}
            </div>
          </fieldset>
          {/* HU-71: con sugerencias mientras se escribe; elegir una guarda sus coordenadas. */}
          <CampoDireccionFormulario
            control={control}
            name="origen_dir"
            coordenadas="origen_coordenadas"
            etiqueta="Origen"
            error={errors.origen_dir?.message ?? errors.origen_coordenadas?.message}
            ancho
            buscar={buscar}
          />
          <CampoDireccionFormulario
            control={control}
            name="destino_dir"
            coordenadas="destino_coordenadas"
            etiqueta="Destino"
            error={errors.destino_dir?.message ?? errors.destino_coordenadas?.message}
            ancho
            buscar={buscar}
          />
          <div className={s.ancho}>
            <MapaDirecciones tipo={tipoDeMapa(sentido)} origen={puntoOrigen} destino={puntoDestino} chico />
          </div>
          <Controller
            control={control}
            name="recogida"
            render={({ field }) => (
              <CampoFechaHora
                etiqueta="Recogida"
                nombre="recogida"
                valor={field.value}
                alCambiar={field.onChange}
                alSalir={field.onBlur}
                refCampo={field.ref}
                error={errors.recogida?.message}
                ayuda="Hora de Chile continental (Santiago)."
              />
            )}
          />
        </div>
      </fieldset>

      {sentido === 'DESDE_AEROPUERTO' ? (
        <fieldset className={`${s.seccion} ${s.seccionVuelo}`} disabled={bloqueado}>
          <legend className={s.leyenda}>Vuelo (opcional)</legend>
          <div className={s.gridCampos}>
            <Campo etiqueta="Número de vuelo" error={errors.vuelo?.numero?.message}>
              {(control) => (
                <input autoComplete="off" autoCapitalize="characters" placeholder="LA123" {...control} {...register('vuelo.numero')} />
              )}
            </Campo>
            <Controller
              control={control}
              name="vuelo.hora"
              render={({ field }) => (
                <CampoFechaHora
                  etiqueta="Llegada programada"
                  nombre="vuelo-hora"
                  valor={field.value}
                  alCambiar={field.onChange}
                  alSalir={field.onBlur}
                  refCampo={field.ref}
                  error={errors.vuelo?.hora?.message}
                />
              )}
            />
          </div>
        </fieldset>
      ) : (
        modo === 'editar' &&
        viaje?.vuelo && <Aviso>Al guardar con este sentido se quitará el vuelo registrado ({viaje.vuelo.numero}).</Aviso>
      )}

      {sentido === 'HACIA_AEROPUERTO' && (
        // HU-69 (DC-70): los mismos datos opcionales del portal; no se monitorean. Con la hora y el tipo, la
        // reserva muestra a qué hora debe estar el pasajero en el aeropuerto.
        <fieldset className={`${s.seccion} ${s.seccionVuelo}`} disabled={bloqueado}>
          <legend className={s.leyenda}>Vuelo de salida (opcional)</legend>
          <div className={s.gridCampos}>
            <Campo etiqueta="Número de vuelo (opcional)" error={errors.vuelo_salida_numero?.message}>
              {(control) => (
                <input autoComplete="off" autoCapitalize="characters" placeholder="Por ejemplo, LA 601" {...control} {...register('vuelo_salida_numero')} />
              )}
            </Campo>
            <Controller
              control={control}
              name="vuelo_salida_hora"
              render={({ field }) => (
                <CampoFechaHora
                  etiqueta="Hora de salida"
                  nombre="vuelo-salida-hora"
                  valor={field.value}
                  alCambiar={field.onChange}
                  alSalir={field.onBlur}
                  refCampo={field.ref}
                  error={errors.vuelo_salida_hora?.message}
                />
              )}
            />
            <fieldset className={`${s.grupoOpciones} ${s.ancho}`}>
              <legend className={s.leyendaOpciones}>Tipo de vuelo</legend>
              <div className={s.pastillas}>
                {(['NACIONAL', 'INTERNACIONAL'] as const).map((tipoVuelo) => (
                  <label key={tipoVuelo} className={s.pastilla}>
                    <input type="radio" className={s.radioOculto} value={tipoVuelo} {...register('vuelo_salida_tipo')} />
                    {tipoVuelo === 'NACIONAL' ? 'Nacional' : 'Internacional'}
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
        </fieldset>
      )}

      <div className={s.pie}>
        <button type="submit" className={estilos.boton} disabled={bloqueado || isSubmitting}>
          {isSubmitting ? 'Guardando…' : modo === 'crear' ? 'Guardar reserva' : 'Guardar cambios'}
        </button>
        <Link to={volverA} className={estilos.botonSecundario}>
          Volver
        </Link>
      </div>
    </form>
  );
}
