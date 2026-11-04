import { useEffect, useRef, useState } from 'react';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { formatearFechaHora } from '../../hora/hora';
import { useAsignarViaje, useCandidatos, type ViajeDetalle } from '../api';
import { mensajeDeErrorApi } from '../errores';

function distancia(metros: number | null): string {
  if (metros === null) return 'sin posición';
  return metros < 1000 ? `a ${metros} m` : `a ${(metros / 1000).toFixed(1).replace('.', ',')} km`;
}

/**
 * Asignar la reserva a un conductor (HU-14, HU-04). Propone al más apto y deja elegir entre los demás Disponibles sin
 * viaje en ejecución (RN-01, RN-03). Nada se asigna hasta que el despachador lo confirma con el botón (RN-02).
 */
export function DialogoAsignar({ viaje, alCerrar, alAsignar }: { viaje: ViajeDetalle; alCerrar: () => void; alAsignar: (nombre: string) => void }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const candidatos = useCandidatos(viaje.id, true);
  const asignar = useAsignarViaje(viaje.id);
  const [falla, setFalla] = useState<string | null>(null);
  const [elegido, setElegido] = useState('');

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

  async function confirmar(id: number, nombre: string) {
    setFalla(null);
    try {
      await asignar.mutateAsync(id);
      alAsignar(nombre);
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
      setElegido('');
      void candidatos.refetch();
    }
  }

  const lista = candidatos.data ?? [];
  const sugerido = lista.find((c) => c.sugerido);
  const otros = lista.filter((c) => !c.sugerido);
  const otroElegido = otros.find((c) => String(c.id) === elegido);

  return (
    <dialog
      ref={dialogo}
      className={estilos.dialogo}
      aria-labelledby="titulo-asignar"
      onCancel={(evento) => {
        evento.preventDefault();
        if (!asignar.isPending) alCerrar();
      }}
    >
      <div className={estilos.formularioDialogo}>
        <h2 id="titulo-asignar">Asignar la reserva #{viaje.id}</h2>
        <p>
          {viaje.pasajero.nombre} · {viaje.origen.direccion} → {viaje.destino.direccion}
        </p>
        {falla && <Aviso tipo="error">{falla}</Aviso>}
        {candidatos.isPending ? (
          <p>Buscando conductores disponibles…</p>
        ) : candidatos.isError ? (
          <Aviso tipo="error">{mensajeDeErrorApi(candidatos.error)}</Aviso>
        ) : lista.length === 0 ? (
          <p>No hay conductores Disponibles sin viaje en este momento.</p>
        ) : (
          <>
            {sugerido ? (
              <ul className={estilos.listaAcciones} aria-label="Conductor sugerido">
                <li>
                  <span>
                    <strong>Sugerido: {sugerido.nombre}</strong> · {sugerido.patente}
                    <span className={estilos.secundario}>
                      {distancia(sugerido.distancia_m)} del origen ·{' '}
                      {sugerido.ultimo_viaje_en ? `último viaje ${formatearFechaHora(sugerido.ultimo_viaje_en)}` : 'sin viajes terminados'}
                    </span>
                  </span>
                  <button type="button" className={estilos.boton} disabled={asignar.isPending} aria-label={`Asignar a ${sugerido.nombre}`} onClick={() => void confirmar(sugerido.id, sugerido.nombre)}>
                    Asignar
                  </button>
                </li>
              </ul>
            ) : (
              <p>Sin sugerencia: ningún conductor tiene una posición reciente y precisa. Elige uno de la lista.</p>
            )}
            {otros.length > 0 && (
              <div className={estilos.acciones}>
                <label>
                  {sugerido ? 'Otro conductor disponible' : 'Conductor disponible'}{' '}
                  <select value={elegido} disabled={asignar.isPending} onChange={(evento) => setElegido(evento.target.value)}>
                    <option value="">Elige un conductor…</option>
                    {otros.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} · {c.patente} · {distancia(c.distancia_m)}
                        {c.confiable ? '' : ' (no reciente)'}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className={estilos.botonSecundario}
                  disabled={!otroElegido || asignar.isPending}
                  onClick={() => otroElegido && void confirmar(otroElegido.id, otroElegido.nombre)}
                >
                  Asignar al elegido
                </button>
              </div>
            )}
          </>
        )}
        <p className={estilos.explicacion}>El conductor tiene 60 s para aceptar en la app; si no responde, la reserva vuelve a Solicitado.</p>
        <div className={estilos.acciones}>
          <button type="button" className={estilos.botonSecundario} onClick={alCerrar} disabled={asignar.isPending}>
            Volver
          </button>
        </div>
      </div>
    </dialog>
  );
}
