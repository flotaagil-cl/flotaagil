import type { EstadoViaje } from '../api';
import { ESTADOS, GRUPO_ESTADO } from '../etiquetas';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';

/** CC-27: cada estado lleva ícono y texto; sus colores no cambian con la paleta de la empresa. */
const ICONO_DE_GRUPO = { pendiente: 'reloj', curso: 'volante', fin: 'check', cancelado: 'cerrar' } as const;

/** Estado del viaje con texto (el color solo acompaña). */
/** CC-22 (HU-52): una pendiente con el plazo vencido se muestra «Sin confirmar», con el color de alerta. */
export function EstadoEtiqueta({ estado, sinConfirmar = false }: { estado: EstadoViaje; sinConfirmar?: boolean }) {
  if (sinConfirmar && estado === 'PENDIENTE_CONFIRMACION') {
    return (
      <span className={`${estilos.etiqueta} ${estilos.alerta}`}>
        <Icono nombre="alerta" tamano={14} className={estilos.iconoEtiqueta} />
        Sin confirmar
      </span>
    );
  }
  const grupo = GRUPO_ESTADO[estado];
  return (
    <span className={`${estilos.etiqueta} ${estilos[grupo]}`}>
      <Icono nombre={ICONO_DE_GRUPO[grupo]} tamano={14} className={estilos.iconoEtiqueta} />
      {ESTADOS[estado]}
    </span>
  );
}
