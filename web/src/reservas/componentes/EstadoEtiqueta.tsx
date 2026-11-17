import type { EstadoViaje } from '../api';
import { ESTADOS, GRUPO_ESTADO } from '../etiquetas';
import estilos from '../../componentes/panel.module.css';

/** Estado del viaje con texto (el color solo acompaña). */
/** CC-22 (HU-52): una pendiente con el plazo vencido se muestra «Sin confirmar», con el color de alerta. */
export function EstadoEtiqueta({ estado, sinConfirmar = false }: { estado: EstadoViaje; sinConfirmar?: boolean }) {
  if (sinConfirmar && estado === 'PENDIENTE_CONFIRMACION') {
    return <span className={`${estilos.etiqueta} ${estilos.alerta}`}>Sin confirmar</span>;
  }
  return <span className={`${estilos.etiqueta} ${estilos[GRUPO_ESTADO[estado]]}`}>{ESTADOS[estado]}</span>;
}
