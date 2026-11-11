import { useId } from 'react';
import e from './diseno.module.css';
import { Icono } from './Icono';

interface Props {
  etiqueta: string;
  /** Lo que se cuenta, en singular, para los botones: «Quitar un pasajero». */
  unidad: string;
  valor: number;
  min?: number;
  max: number;
  onCambiar: (valor: number) => void;
  error?: string;
}

/** Contador con botones − y + de 44 px (pasajeros, maletas). El valor se anuncia al cambiar. */
export function Contador({ etiqueta, unidad, valor, min = 0, max, onCambiar, error }: Props) {
  const id = useId();
  return (
    <div className={e.contador} role="group" aria-labelledby={`${id}-etiqueta`} aria-describedby={error ? `${id}-error` : undefined}>
      <span id={`${id}-etiqueta`} className={e.etiqueta}>
        {etiqueta}
      </span>
      <div className={e.contadorFila}>
        <button type="button" className={e.contadorBoton} aria-label={`Quitar un ${unidad}`} disabled={valor <= min} onClick={() => onCambiar(valor - 1)}>
          <Icono nombre="menos" tamano={18} />
        </button>
        <output className={e.contadorValor} aria-live="polite" aria-atomic="true">
          {valor}
        </output>
        <button type="button" className={e.contadorBoton} aria-label={`Agregar un ${unidad}`} disabled={valor >= max} onClick={() => onCambiar(valor + 1)}>
          <Icono nombre="mas" tamano={18} />
        </button>
      </div>
      {error && (
        <p id={`${id}-error`} className={e.errorCampo}>
          {error}
        </p>
      )}
    </div>
  );
}
