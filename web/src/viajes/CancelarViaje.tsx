import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { components } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { Boton } from '../diseno/Boton';
import { Dialogo } from '../diseno/Dialogo';
import e from '../diseno/diseno.module.css';
import { useApi } from '../sesion/SesionProvider';

type Motivo = components['schemas']['MotivoEnum'];

const MOTIVOS: { valor: Motivo; texto: string }[] = [
  { valor: 'CAMBIO_DE_PLANES', texto: 'Cambié de planes' },
  { valor: 'VUELO_CANCELADO', texto: 'Mi vuelo se canceló' },
  { valor: 'OTRO', texto: 'Otro motivo' },
];

/**
 * HU-44 (RN-09): cancelar desde la cuenta, solo sin conductor asignado, con confirmación y motivo. Si el viaje ya
 * tomó conductor (409), lo dice y pide contactar a la central.
 */
export function CancelarViaje({ id, resumen }: { id: number; resumen: string }) {
  const api = useApi();
  const consultas = useQueryClient();
  const [abierto, setAbierto] = useState(false);
  const [motivo, setMotivo] = useState<Motivo>('CAMBIO_DE_PLANES');
  const [falla, setFalla] = useState<string | null>(null);
  const cancelar = useMutation({
    mutationFn: () => resultado(api.POST('/api/mi-cuenta/reservas/{id}/cancelar/', { params: { path: { id } }, body: { motivo } })),
    onSuccess: () => {
      setAbierto(false);
      void consultas.invalidateQueries({ queryKey: ['mi-cuenta'] });
    },
    onError: (error) => {
      setFalla(
        error instanceof ErrorApi && error.estado === 409
          ? 'Tu viaje ya tiene conductor asignado: para cancelar, contacta a la central.'
          : 'No se pudo cancelar. Intenta de nuevo.',
      );
    },
  });

  return (
    <>
      <button type="button" className={e.botonEnlacePeligro} onClick={() => { setFalla(null); setAbierto(true); }}>
        Cancelar viaje
      </button>
      <Dialogo abierto={abierto} titulo="¿Cancelar este viaje?" onCerrar={() => setAbierto(false)}>
        <div className={e.formulario}>
          <p className={e.saludo}>{resumen}. La central quedará avisada.</p>
          <fieldset className={e.segmentado}>
            <legend className={e.etiqueta}>Motivo</legend>
            <div className={e.radios}>
              {MOTIVOS.map((m) => (
                <label key={m.valor} className={e.casilla}>
                  <input type="radio" name={`motivo-${id}`} value={m.valor} checked={motivo === m.valor} onChange={() => setMotivo(m.valor)} />
                  <span>{m.texto}</span>
                </label>
              ))}
            </div>
          </fieldset>
          {falla && (
            <p className={e.alerta} role="alert">
              {falla}
            </p>
          )}
          <Boton variante="peligro" ancho cargando={cancelar.isPending} onClick={() => cancelar.mutate()}>
            {cancelar.isPending ? 'Cancelando…' : 'Sí, cancelar viaje'}
          </Boton>
          <Boton variante="secundario" ancho onClick={() => setAbierto(false)}>
            Volver
          </Boton>
        </div>
      </Dialogo>
    </>
  );
}
