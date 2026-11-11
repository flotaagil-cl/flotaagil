import { useId, type ComponentProps, type ReactNode } from 'react';
import e from './diseno.module.css';
import { Icono } from './Icono';
import type { NombreIcono } from './iconos';

interface PropsCampo extends ComponentProps<'input'> {
  etiqueta: string;
  /** Mensaje de error: queda fuera de la etiqueta y se asocia con aria-describedby. */
  error?: string;
  ayuda?: ReactNode;
  icono?: NombreIcono;
}

/** Campo de texto con su etiqueta. Acepta `ref` (React 19), así sirve con react-hook-form. */
export function Campo({ etiqueta, error, ayuda, icono, id, className, ...resto }: PropsCampo) {
  const generado = useId();
  const idCampo = id ?? generado;
  const describe = [ayuda ? `${idCampo}-ayuda` : null, error ? `${idCampo}-error` : null].filter(Boolean).join(' ');
  return (
    <div className={[e.campo, className].filter(Boolean).join(' ')}>
      <label htmlFor={idCampo} className={e.etiqueta}>
        {etiqueta}
      </label>
      <div className={icono ? `${e.control} ${e.conIcono}` : e.control}>
        {icono && <Icono nombre={icono} />}
        <input
          id={idCampo}
          className={e.entrada}
          aria-invalid={error ? true : undefined}
          aria-describedby={describe || undefined}
          {...resto}
        />
      </div>
      {ayuda && (
        <p id={`${idCampo}-ayuda`} className={e.ayuda}>
          {ayuda}
        </p>
      )}
      {error && (
        <p id={`${idCampo}-error`} className={e.errorCampo}>
          {error}
        </p>
      )}
    </div>
  );
}

interface PropsDatoFijo {
  etiqueta: string;
  valor: string;
  icono?: NombreIcono;
}

/** Dato que no se puede cambiar (por ejemplo, el aeropuerto de origen): se ve como un campo bloqueado. */
export function DatoFijo({ etiqueta, valor, icono = 'avion' }: PropsDatoFijo) {
  return (
    <div className={e.datoFijo}>
      <Icono nombre={icono} />
      <p className={e.datoFijoTexto}>
        <span className={e.datoFijoEtiqueta}>{etiqueta}</span>
        <span className={e.datoFijoValor}>{valor}</span>
      </p>
      <Icono nombre="candado" tamano={16} className={e.datoFijoCandado} />
      <span className="solo-lector">(no se puede cambiar)</span>
    </div>
  );
}
