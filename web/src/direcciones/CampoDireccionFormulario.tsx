import { useController, type Control, type FieldPath, type FieldValues } from 'react-hook-form';
import { Campo } from '../formularios/Campo';
import { ConSugerencias } from './ConSugerencias';
import { useCombobox } from './useCombobox';
import type { Buscar } from './sugerencias';

interface Props<T extends FieldValues> {
  control: Control<T>;
  /** Campo del texto (p. ej. `origen_dir`). */
  name: FieldPath<T>;
  /** Campo de las coordenadas de la sugerencia (p. ej. `origen_coordenadas`); null si se escribe a mano. */
  coordenadas: FieldPath<T>;
  etiqueta: string;
  error?: string;
  ancho?: boolean;
  buscar: Buscar;
}

/** HU-71: campo de dirección con sugerencias para los formularios con react-hook-form (panel y convenio). */
export function CampoDireccionFormulario<T extends FieldValues>({ control, name, coordenadas, etiqueta, error, ancho, buscar }: Props<T>) {
  const texto = useController({ control, name });
  const ubicacion = useController({ control, name: coordenadas });
  const { entrada, lista } = useCombobox({
    valor: (texto.field.value as string | undefined) ?? '',
    alCambiar: (valor) => {
      texto.field.onChange(valor);
      if (ubicacion.field.value) ubicacion.field.onChange(null);
    },
    alElegir: (sugerencia) => {
      texto.field.onChange(sugerencia.texto);
      ubicacion.field.onChange({ lat: sugerencia.lat, lon: sugerencia.lon });
    },
    buscar,
  });
  return (
    <Campo etiqueta={etiqueta} error={error} ancho={ancho}>
      {(atributos) => (
        <ConSugerencias lista={lista}>
          <input
            {...atributos}
            {...entrada}
            name={texto.field.name}
            ref={texto.field.ref}
            onBlur={(evento) => {
              entrada.onBlur?.(evento);
              texto.field.onBlur();
            }}
          />
        </ConSugerencias>
      )}
    </Campo>
  );
}
