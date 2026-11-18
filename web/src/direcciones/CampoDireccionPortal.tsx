import { Campo } from '../diseno/Campo';
import { ConSugerencias } from './ConSugerencias';
import type { Buscar, Sugerencia } from './sugerencias';
import { useCombobox } from './useCombobox';

interface Props {
  etiqueta: string;
  placeholder?: string;
  valor: string;
  error?: string;
  alCambiar: (texto: string) => void;
  alElegir: (sugerencia: Sugerencia) => void;
  buscar: Buscar;
}

/** HU-71: campo de dirección con sugerencias para el pedido del portal (sistema visual CC-20). */
export function CampoDireccionPortal({ etiqueta, placeholder, valor, error, alCambiar, alElegir, buscar }: Props) {
  const { entrada, lista } = useCombobox({ valor, alCambiar, alElegir, buscar });
  return (
    <ConSugerencias lista={lista}>
      <Campo etiqueta={etiqueta} placeholder={placeholder} error={error} {...entrada} />
    </ConSugerencias>
  );
}
