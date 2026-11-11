import { useId } from 'react';
import e from './diseno.module.css';

interface Props<T extends string> {
  etiqueta: string;
  opciones: { valor: T; texto: string }[];
  valor: T;
  onCambiar: (valor: T) => void;
  /** «pastillas»: botones separados (Ahora / Programar); «bloque»: control segmentado (Nacional / Internacional). */
  forma?: 'bloque' | 'pastillas';
}

/** Elección entre pocas opciones con radios nativos (flechas del teclado incluidas), con zonas de 44 px. */
export function Segmentado<T extends string>({ etiqueta, opciones, valor, onCambiar, forma = 'bloque' }: Props<T>) {
  const nombre = useId();
  return (
    <fieldset className={e.segmentado} data-forma={forma}>
      <legend className={e.etiqueta}>{etiqueta}</legend>
      <div className={e.segmentadoOpciones}>
        {opciones.map((opcion) => (
          <label key={opcion.valor} className={e.segmentadoOpcion}>
            <input type="radio" name={nombre} value={opcion.valor} checked={opcion.valor === valor} onChange={() => onCambiar(opcion.valor)} />
            <span>{opcion.texto}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
