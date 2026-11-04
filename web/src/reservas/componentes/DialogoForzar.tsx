import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { useForzarCierre, type ViajeDetalle } from '../api';
import { mensajeDeErrorApi } from '../errores';
import { METODOS_PAGO } from '../etiquetas';

const MAXIMO_MOTIVO = 200;
const MONTO_MAXIMO = 500_000;

/** Acepta «15000» y «15.000». */
export function leerMonto(texto: string): number | null {
  const limpio = texto.trim().replace(/[.\s]/g, '').replace(/^\$/, '');
  return /^\d+$/.test(limpio) ? Number(limpio) : null;
}

const esquema = z
  .object({
    accion: z.enum(['ANULAR', 'CERRAR']),
    motivo: z
      .string()
      .trim()
      .min(1, { error: 'Indica el motivo.' })
      .max(MAXIMO_MOTIVO, { error: `Máximo ${MAXIMO_MOTIVO} caracteres.` }),
    metodo: z.string(),
    monto: z.string(),
  })
  .superRefine((datos, contexto) => {
    if (datos.accion !== 'CERRAR') return;
    if (!datos.metodo) contexto.addIssue({ code: 'custom', path: ['metodo'], message: 'Elige el método de pago.' });
    const monto = leerMonto(datos.monto);
    if (monto === null) contexto.addIssue({ code: 'custom', path: ['monto'], message: 'Ingresa el monto cobrado, en pesos enteros.' });
    else if (monto > MONTO_MAXIMO) contexto.addIssue({ code: 'custom', path: ['monto'], message: 'El monto máximo es $500.000.' });
  });

type Datos = z.infer<typeof esquema>;

interface Props {
  viaje: ViajeDetalle;
  alCerrar: () => void;
  alTerminar: (texto: string) => void;
}

/** HU-05: con el pasajero a bordo y el conductor sin conexión. Queda en auditoría con el responsable (RN-11). */
export function DialogoForzar({ viaje, alCerrar, alTerminar }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const forzar = useForzarCierre(viaje.id);
  const [falla, setFalla] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { accion: 'CERRAR', motivo: '', metodo: viaje.convenio ? 'CONVENIO' : '', monto: viaje.tarifa === null ? '' : String(viaje.tarifa) },
  });
  const accion = useWatch({ control, name: 'accion' });
  const motivo = useWatch({ control, name: 'motivo' });
  const metodos = Object.entries(METODOS_PAGO).filter(([valor]) => valor !== 'CONVENIO' || viaje.convenio);

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

  async function confirmar(datos: Datos) {
    setFalla(null);
    try {
      await forzar.mutateAsync(
        datos.accion === 'ANULAR'
          ? { accion: 'ANULAR', motivo: datos.motivo }
          : { accion: 'CERRAR', motivo: datos.motivo, metodo: datos.metodo as keyof typeof METODOS_PAGO, monto: leerMonto(datos.monto)! },
      );
      alTerminar(datos.accion === 'ANULAR' ? 'Viaje anulado.' : 'Viaje cerrado con su pago.');
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    }
  }

  return (
    <dialog
      ref={dialogo}
      className={estilos.dialogo}
      aria-labelledby="titulo-forzar"
      onCancel={(evento) => {
        evento.preventDefault();
        if (!forzar.isPending) alCerrar();
      }}
    >
      <form onSubmit={handleSubmit(confirmar)} noValidate>
        <h2 id="titulo-forzar">Cierre o anulación forzada de la reserva #{viaje.id}</h2>
        <p>
          {viaje.pasajero.nombre} · {viaje.conductor?.nombre ?? 'Sin conductor'} · {viaje.origen.direccion} → {viaje.destino.direccion}
        </p>
        <Aviso tipo="error">Úsalo solo si el conductor no puede hacerlo desde la app. Queda en auditoría con tu nombre y el conductor vuelve a Disponible.</Aviso>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <fieldset className={estilos.opciones}>
          <legend>Qué hacer</legend>
          <label>
            <input type="radio" value="CERRAR" {...register('accion')} /> Cerrar: el viaje se hizo y se cobró
          </label>
          <label>
            <input type="radio" value="ANULAR" {...register('accion')} /> Anular: el viaje no se completó
          </label>
        </fieldset>
        <Campo etiqueta="Motivo" error={errors.motivo?.message}>
          {(control) => <textarea rows={3} maxLength={MAXIMO_MOTIVO} {...control} {...register('motivo')} />}
        </Campo>
        <span className={estilos.contador} aria-live="polite">
          {motivo.length}/{MAXIMO_MOTIVO}
        </span>
        {accion === 'CERRAR' && (
          <>
            <Campo etiqueta="Método de pago" error={errors.metodo?.message}>
              {(control) => (
                <select {...control} {...register('metodo')}>
                  <option value="">Elige un método…</option>
                  {metodos.map(([valor, texto]) => (
                    <option key={valor} value={valor}>
                      {texto}
                    </option>
                  ))}
                </select>
              )}
            </Campo>
            <Campo etiqueta="Monto cobrado (CLP)" error={errors.monto?.message}>
              {(control) => <input inputMode="numeric" autoComplete="off" {...control} {...register('monto')} />}
            </Campo>
          </>
        )}
        <div className={estilos.acciones}>
          <button type="submit" className={estilos.botonPeligro} disabled={forzar.isPending}>
            {forzar.isPending ? 'Guardando…' : accion === 'ANULAR' ? 'Anular viaje' : 'Cerrar viaje'}
          </button>
          <button type="button" className={estilos.botonSecundario} onClick={alCerrar} disabled={forzar.isPending}>
            Volver
          </button>
        </div>
      </form>
    </dialog>
  );
}
