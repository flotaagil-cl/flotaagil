import { useEffect, useRef, useState } from 'react';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { useAsignarViaje, useCandidatos, type ViajeDetalle } from '../api';
import { mensajeDeErrorApi } from '../errores';

function distancia(metros: number | null): string {
  if (metros === null) return 'sin posición reciente';
  return metros < 1000 ? `a ${metros} m` : `a ${(metros / 1000).toFixed(1).replace('.', ',')} km`;
}

/**
 * Asignar la reserva a un conductor (HU-14). El despachador elige entre los Disponibles sin viaje en ejecución
 * (RN-01, RN-03), los más cercanos al origen primero; su elección es la confirmación (RN-02).
 */
export function DialogoAsignar({ viaje, alCerrar, alAsignar }: { viaje: ViajeDetalle; alCerrar: () => void; alAsignar: (nombre: string) => void }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const candidatos = useCandidatos(viaje.id, true);
  const asignar = useAsignarViaje(viaje.id);
  const [falla, setFalla] = useState<string | null>(null);

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

  async function elegir(id: number, nombre: string) {
    setFalla(null);
    try {
      await asignar.mutateAsync(id);
      alAsignar(nombre);
    } catch (error) {
      setFalla(mensajeDeErrorApi(error));
      void candidatos.refetch();
    }
  }

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
        ) : candidatos.data.length === 0 ? (
          <p>No hay conductores Disponibles sin viaje en este momento.</p>
        ) : (
          <ul className={estilos.listaAcciones} aria-label="Conductores disponibles">
            {candidatos.data.map((c) => (
              <li key={c.id}>
                <span>
                  <strong>{c.nombre}</strong> · {c.patente}
                  <span className={estilos.secundario}>{distancia(c.distancia_m)} del origen</span>
                </span>
                <button type="button" className={estilos.boton} disabled={asignar.isPending} aria-label={`Asignar a ${c.nombre}`} onClick={() => void elegir(c.id, c.nombre)}>
                  Asignar
                </button>
              </li>
            ))}
          </ul>
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
