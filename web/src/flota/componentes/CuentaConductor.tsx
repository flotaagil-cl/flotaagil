import { useEffect, useRef, useState } from 'react';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { formatearFechaHora } from '../../hora/hora';
import { useGenerarPassword, useHabilitacion, type Acceso, type Conductor } from '../api';
import { mensajeDeError } from '../errores';

const ACCESOS: Record<Acceso, string> = {
  SIN_PASSWORD: 'Sin contraseña: todavía no puede ingresar a la app.',
  TEMPORAL: 'Con contraseña temporal: debe cambiarla al ingresar.',
  TEMPORAL_VENCIDA: 'La contraseña temporal venció sin usarse: genera otra.',
  ACTIVA: 'Con contraseña propia.',
};

type Confirmando = 'password' | 'deshabilitar' | null;

/** Cuenta del conductor: contraseña temporal (se muestra una sola vez) y habilitación. */
export function CuentaConductor({ conductor }: { conductor: Conductor }) {
  const generar = useGenerarPassword(conductor.id);
  const habilitacion = useHabilitacion(conductor.id);
  const [confirmando, setConfirmando] = useState<Confirmando>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  // La temporal vive solo aquí, en memoria, hasta cerrar el diálogo.
  const [temporal, setTemporal] = useState<{ password: string; vence: string } | null>(null);
  const ocupado = generar.isPending || habilitacion.isPending;
  const primera = conductor.acceso === 'SIN_PASSWORD';

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
    <div className={estilos.tarjeta}>
      <h2>Cuenta</h2>
      {aviso && <Aviso>{aviso}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <p>
        {conductor.activo ? ACCESOS[conductor.acceso] : 'Deshabilitada: no puede ingresar a la app.'}
        {conductor.activo && conductor.acceso === 'TEMPORAL' && conductor.password_temporal_vence && (
          <span className={estilos.secundario}> Vence el {formatearFechaHora(conductor.password_temporal_vence)}.</span>
        )}
      </p>

      {confirmando ? (
        <div className={estilos.confirmacion} role="group" aria-label="Confirmar">
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
        <div className={estilos.acciones}>
          {conductor.activo && (
            <button type="button" className={estilos.boton} disabled={ocupado} onClick={() => setConfirmando('password')}>
              {primera ? 'Generar contraseña temporal' : 'Restablecer contraseña'}
            </button>
          )}
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
        <h2 id="titulo-password">Contraseña temporal</h2>
        <p>
          Entrégasela {quien} para su primer ingreso con <strong>{correo}</strong>. No se volverá a mostrar: si se
          pierde, genera otra.
        </p>
        <p className={estilos.password} aria-label="Contraseña temporal">
          {password}
        </p>
        <p className={estilos.secundario}>Vence el {formatearFechaHora(vence)} si no se usa. Al ingresar, deberá cambiarla.</p>
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
