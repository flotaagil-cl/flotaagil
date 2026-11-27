import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { Campo } from '../../formularios/Campo';
import { formatearFechaHora } from '../../hora/hora';
import { useCambiarCorreo, useGenerarPassword, useHabilitacion, type Acceso, type Conductor } from '../api';
import { mensajeDeError } from '../errores';
import { ACCESOS_APP } from '../etiquetas';
import s from '../flota.module.css';

const ACCESOS: Record<Acceso, string> = {
  SIN_PASSWORD: 'Sin contraseña: todavía no puede ingresar a la app.',
  TEMPORAL: 'Con contraseña temporal: debe cambiarla al ingresar.',
  TEMPORAL_VENCIDA: 'La contraseña temporal venció sin usarse: genera otra.',
  ACTIVA: 'Con contraseña propia.',
};

type Tono = 'ok' | 'revision' | 'peligro' | 'neutro';

const TONO_ACCESO: Record<keyof typeof ACCESOS_APP, Tono> = {
  ACTIVA: 'ok',
  TEMPORAL: 'revision',
  TEMPORAL_VENCIDA: 'peligro',
  SIN_PASSWORD: 'peligro',
  DESHABILITADA: 'neutro',
};

type Confirmando = 'password' | 'deshabilitar' | null;

/**
 * HU-74 (DC-78): «Acceso a la app» del conductor. Correo de acceso, estado y último ingreso; contraseña temporal
 * (se muestra una sola vez), cambio de correo y habilitación. Todo cierra las sesiones del conductor cuando corresponde.
 */
export function CuentaConductor({ conductor }: { conductor: Conductor }) {
  const generar = useGenerarPassword(conductor.id);
  const habilitacion = useHabilitacion(conductor.id);
  const [confirmando, setConfirmando] = useState<Confirmando>(null);
  const [cambiandoCorreo, setCambiandoCorreo] = useState(false);
  const [falla, setFalla] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  // La temporal vive solo aquí, en memoria, hasta cerrar el diálogo.
  const [temporal, setTemporal] = useState<{ password: string; vence: string } | null>(null);
  const ocupado = generar.isPending || habilitacion.isPending;
  const primera = conductor.acceso === 'SIN_PASSWORD';
  const claveAcceso = conductor.activo ? conductor.acceso : 'DESHABILITADA';

  async function confirmar() {
    setFalla(null);
    setAviso(null);
    try {
      if (confirmando === 'password') {
        const { password_temporal, vence_en } = await generar.mutateAsync();
        setTemporal({ password: password_temporal, vence: vence_en });
      } else {
        await habilitacion.mutateAsync(false);
        setAviso('Cuenta deshabilitada. Sus sesiones se cerraron.');
      }
    } catch (error) {
      setFalla(mensajeDeError(error, 'el conductor'));
    } finally {
      setConfirmando(null);
    }
  }

  async function habilitar() {
    setFalla(null);
    setAviso(null);
    try {
      await habilitacion.mutateAsync(true);
      setAviso('Cuenta habilitada.');
    } catch (error) {
      setFalla(mensajeDeError(error, 'el conductor'));
    }
  }

  return (
    <div className={s.tarjeta}>
      {/* Nota: <h2> permanece hijo directo de la tarjeta (cuentas.test.tsx busca parentElement). */}
      <h2>Acceso a la app</h2>
      {aviso && <Aviso>{aviso}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <dl className={s.datosGrid}>
        <div className={s.datoItem}>
          <dt>Correo de acceso</dt>
          <dd>{conductor.email}</dd>
        </div>
        <div className={s.datoItem}>
          <dt>Último ingreso</dt>
          <dd>{conductor.ultimo_ingreso ? formatearFechaHora(conductor.ultimo_ingreso) : 'Todavía no ingresa'}</dd>
        </div>
        <div className={s.datoItem}>
          <dt>Estado</dt>
          <dd>
            <span className={s.estadoDetalleAcceso} data-tono={TONO_ACCESO[claveAcceso]}>
              {conductor.activo ? ACCESOS[conductor.acceso] : 'Deshabilitada: no puede ingresar a la app.'}
            </span>
            {conductor.activo && conductor.acceso === 'TEMPORAL' && conductor.password_temporal_vence && (
              <span className={s.secundario}>Vence el {formatearFechaHora(conductor.password_temporal_vence)}.</span>
            )}
          </dd>
        </div>
      </dl>

      {cambiandoCorreo ? (
        <CambiarCorreo
          conductor={conductor}
          alCerrar={(mensaje) => {
            setCambiandoCorreo(false);
            if (mensaje) setAviso(mensaje);
          }}
        />
      ) : confirmando ? (
        <div className={confirmando === 'deshabilitar' ? s.panelPeligro : s.panelConfirmacion} role="group" aria-label="Confirmar">
          <p>
            {confirmando === 'password'
              ? primera
                ? 'Se generará una contraseña temporal. Se mostrará una sola vez.'
                : 'Se generará una contraseña temporal nueva: la actual dejará de servir y se cerrarán todas las sesiones del conductor.'
              : 'El conductor no podrá ingresar, se cerrarán todas sus sesiones y quedará No disponible.'}
          </p>
          <div className={estilos.acciones}>
            <button
              type="button"
              className={confirmando === 'password' ? estilos.boton : estilos.botonPeligro}
              disabled={ocupado}
              onClick={() => void confirmar()}
            >
              {confirmando === 'password' ? 'Generar' : 'Deshabilitar'}
            </button>
            <button type="button" className={estilos.botonSecundario} disabled={ocupado} onClick={() => setConfirmando(null)}>
              Volver
            </button>
          </div>
        </div>
      ) : (
        <div className={s.bloqueAcciones}>
          {conductor.activo && (
            <button
              type="button"
              className={`${estilos.boton} ${s.botonConIcono}`}
              disabled={ocupado}
              onClick={() => setConfirmando('password')}
            >
              <Icono nombre="llave" tamano={16} />
              {primera ? 'Generar contraseña temporal' : 'Restablecer contraseña'}
            </button>
          )}
          <button
            type="button"
            className={estilos.botonSecundario}
            disabled={ocupado}
            onClick={() => {
              setAviso(null);
              setFalla(null);
              setCambiandoCorreo(true);
            }}
          >
            Cambiar correo
          </button>
          {conductor.activo ? (
            <button type="button" className={estilos.botonPeligro} disabled={ocupado} onClick={() => setConfirmando('deshabilitar')}>
              Deshabilitar cuenta
            </button>
          ) : (
            <button type="button" className={estilos.boton} disabled={ocupado} onClick={() => void habilitar()}>
              Habilitar cuenta
            </button>
          )}
        </div>
      )}

      {temporal && <DialogoPassword {...temporal} correo={conductor.email} alCerrar={() => setTemporal(null)} />}
    </div>
  );
}

const CORREO_VALIDO = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

/** HU-74 (DC-78): correo de acceso nuevo. Cierra las sesiones del conductor, que entra con el correo nuevo. */
function CambiarCorreo({ conductor, alCerrar }: { conductor: Conductor; alCerrar: (mensaje?: string) => void }) {
  const cambiar = useCambiarCorreo(conductor.id);
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | undefined>();
  const [falla, setFalla] = useState<string | null>(null);

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setFalla(null);
    const valor = email.trim().toLowerCase();
    if (!CORREO_VALIDO.test(valor)) {
      setError('Ingresa un correo válido.');
      return;
    }
    if (valor === conductor.email) {
      setError('Es el mismo correo de acceso actual.');
      return;
    }
    setError(undefined);
    try {
      await cambiar.mutateAsync(valor);
      alCerrar(`Correo de acceso cambiado. Sus sesiones se cerraron: debe entrar con ${valor}.`);
    } catch (e) {
      if (e instanceof ErrorApi && e.estado === 400) {
        const cuerpo = (e.cuerpo ?? {}) as { email?: string[] };
        setError(cuerpo.email?.[0] ?? 'Revisa el correo.');
      } else {
        setFalla(mensajeDeError(e, 'el conductor'));
      }
    }
  }

  return (
    <form className={s.panelConfirmacion} onSubmit={(e) => void enviar(e)} noValidate aria-label="Cambiar correo de acceso">
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <Campo etiqueta="Correo de acceso nuevo" error={error} ayuda="Se cerrarán sus sesiones y deberá entrar a la app con este correo.">
        {(control) => (
          <input {...control} type="email" maxLength={120} autoComplete="off" value={email} onChange={(e) => setEmail(e.target.value)} />
        )}
      </Campo>
      <div className={estilos.acciones}>
        <button type="submit" className={estilos.boton} disabled={cambiar.isPending}>
          {cambiar.isPending ? 'Guardando…' : 'Cambiar correo'}
        </button>
        <button type="button" className={estilos.botonSecundario} disabled={cambiar.isPending} onClick={() => alCerrar()}>
          Volver
        </button>
      </div>
    </form>
  );
}

/** Temporal recién generada (DC-14): se muestra una sola vez. También la usa la pantalla de usuarios (HU-36). */
export function DialogoPassword({
  password,
  vence,
  correo,
  quien = 'al conductor',
  alCerrar,
}: {
  password: string;
  vence: string;
  correo: string;
  quien?: string;
  alCerrar: () => void;
}) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [copiada, setCopiada] = useState<boolean | null>(null);

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento || elemento.open) return;
    if (typeof elemento.showModal === 'function') elemento.showModal();
    else elemento.setAttribute('open', '');
    return () => {
      if (typeof elemento.close === 'function') elemento.close();
      else elemento.removeAttribute('open');
    };
  }, []);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(password);
      setCopiada(true);
    } catch {
      setCopiada(false);
    }
  }

  return (
    <dialog
      ref={dialogo}
      className={estilos.dialogo}
      aria-labelledby="titulo-password"
      onCancel={(evento) => {
        evento.preventDefault();
        alCerrar();
      }}
    >
      <div className={estilos.formularioDialogo}>
        <div className={s.dialogoHeader}>
          <Icono nombre="llave" tamano={20} />
          <h2 id="titulo-password">Contraseña temporal</h2>
        </div>
        <p className={s.subtitulo}>
          Entrégasela {quien} para su primer ingreso con <strong>{correo}</strong>. No se volverá a mostrar: si se
          pierde, genera otra.
        </p>
        <p className={s.cajaPassword} aria-label="Contraseña temporal">
          {password}
        </p>
        <p className={s.secundario}>Vence el {formatearFechaHora(vence)} si no se usa. Al ingresar, deberá cambiarla.</p>
        {copiada === true && <Aviso>Copiada.</Aviso>}
        {copiada === false && <Aviso tipo="error">No se pudo copiar: selecciónala y cópiala a mano.</Aviso>}
        <div className={estilos.acciones}>
          <button type="button" className={estilos.boton} onClick={() => void copiar()}>
            Copiar
          </button>
          <button type="button" className={estilos.botonSecundario} onClick={alCerrar}>
            Listo
          </button>
        </div>
      </div>
    </dialog>
  );
}
