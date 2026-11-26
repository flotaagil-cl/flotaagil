import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect, useRef, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { useCancelarViaje, type ViajeDetalle } from '../api';
import { mensajeDeErrorApi } from '../errores';
import d from './DialogosReserva.module.css';
import { CabeceraDialogo, ResumenViajeDialogo } from './ResumenViajeDialogo';

const MAXIMO = 200;

const esquema = z.object({
  motivo: z
    .string()
    .trim()
    .min(1, { error: 'Indica el motivo de la cancelación.' })
    .max(MAXIMO, { error: `Máximo ${MAXIMO} caracteres.` }),
});

type Datos = z.infer<typeof esquema>;

interface Props {
  viaje: ViajeDetalle;
  alCerrar: () => void;
  alCancelar: () => void;
}

/** Cancelar con motivo obligatorio: el diálogo es la confirmación (botón «Cancelar reserva»). */
export function DialogoCancelar({ viaje, alCerrar, alCancelar }: Props) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const cancelar = useCancelarViaje(viaje.id);
  const [falla, setFalla] = useState<string | null>(null);
  const {
    register,
    control,
    handleSubmit,
    formState: { errors },
  } = useForm<Datos>({ resolver: zodResolver(esquema), defaultValues: { motivo: '' } });
  const motivo = useWatch({ control, name: 'motivo' });

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento || elemento.open) return;
    // Sin showModal (navegadores antiguos, jsdom) se abre como diálogo no modal.
    if (typeof elemento.showModal === 'function') elemento.showModal();
    else elemento.setAttribute('open', '');
    return () => {
      if (typeof elemento.close === 'function') elemento.close();
      else elemento.removeAttribute('open');
    };
  }, []);

  async function confirmar({ motivo }: Datos) {
    setFalla(null);
    try {
      await cancelar.mutateAsync(motivo);
      alCancelar();
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
    }
  }

  return (
    <dialog
      ref={dialogo}
      className={estilos.dialogo}
      aria-labelledby="titulo-cancelar"
      onCancel={(evento) => {
        evento.preventDefault();
        if (!cancelar.isPending) alCerrar();
      }}
    >
      <form onSubmit={handleSubmit(confirmar)} noValidate>
        <CabeceraDialogo tituloId="titulo-cancelar" titulo={`Cancelar la reserva #${viaje.id}`} alCerrar={alCerrar} deshabilitado={cancelar.isPending} />
        <ResumenViajeDialogo viaje={viaje} />
        {viaje.conductor && (
          <Aviso tipo="error">El conductor {viaje.conductor.nombre} ya está asignado a esta reserva.</Aviso>
        )}
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        <Campo etiqueta="Motivo" error={errors.motivo?.message}>
          {(control) => <textarea rows={3} maxLength={MAXIMO} {...control} {...register('motivo')} />}
        </Campo>
        <span className={estilos.contador} aria-live="polite">
          {motivo.length}/{MAXIMO}
        </span>
        <div className={d.pie}>
          <button type="button" className={estilos.botonSecundario} onClick={alCerrar} disabled={cancelar.isPending}>
            Volver
          </button>
          <button type="submit" className={estilos.botonPeligro} disabled={cancelar.isPending}>
            {cancelar.isPending ? 'Cancelando…' : 'Cancelar reserva'}
          </button>
        </div>
      </form>
    </dialog>
  );
}
