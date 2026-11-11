/**
 * HU-43 y HU-44: cómo ve el pasajero su viaje (insignia, avance y si puede cancelar). Funciones puras para
 * probarlas sin pantallas.
 */

import type { components } from '../api/esquema';
import type { TonoInsignia } from '../diseno/Tarjeta';
import type { PasoLinea } from '../diseno/LineaDeTiempo';
import { formatearFechaHora } from '../hora/hora';

export type TuViaje = components['schemas']['TuViaje'];
export type EstadoViaje = components['schemas']['EstadoViajeEnum'];
export type MiViaje = components['schemas']['MiReserva'];

/** Navegación del pasajero con sesión (HU-43, HU-44). */
export const ENLACES_PASAJERO = [
  { a: '/pedir', texto: 'Pedir traslado' },
  { a: '/mis-viajes', texto: 'Mis viajes' },
];

/** Solo en el menú de la cuenta: datos y eliminar la cuenta (pantalla anterior, hasta «Mi perfil» de HU-45). */
export const CUENTA_PASAJERO = [{ a: '/mis-reservas', texto: 'Mi cuenta' }];

export const INSIGNIA: Record<EstadoViaje, { texto: string; tono: TonoInsignia }> = {
  PENDIENTE_CONFIRMACION: { texto: 'Por confirmar', tono: 'revision' },
  SOLICITADO: { texto: 'Buscando conductor', tono: 'neutra' },
  ASIGNADO: { texto: 'Buscando conductor', tono: 'neutra' },
  ACEPTADO: { texto: 'Conductor asignado', tono: 'info' },
  EN_CAMINO: { texto: 'Conductor en camino', tono: 'info' },
  EN_ZONA: { texto: 'Tu conductor llegó', tono: 'ok' },
  PASAJERO_A_BORDO: { texto: 'En viaje', tono: 'ok' },
  FINALIZADO: { texto: 'Finalizado', tono: 'neutra' },
  CANCELADO: { texto: 'Cancelado', tono: 'peligro' },
};

export const TIPO_DE_VIAJE: Record<string, string> = {
  DESDE_AEROPUERTO: 'Desde el aeropuerto',
  HACIA_AEROPUERTO: 'Al aeropuerto',
  URBANO: 'En la ciudad',
};

export const INSIGNIA_VUELO: Record<string, { texto: string; tono: TonoInsignia }> = {
  PROGRAMADO: { texto: 'A tiempo', tono: 'ok' },
  DEMORADO: { texto: 'Atrasado', tono: 'info' },
  ATERRIZADO: { texto: 'Aterrizó', tono: 'ok' },
  CANCELADO: { texto: 'Cancelado', tono: 'peligro' },
  DESVIADO: { texto: 'Desviado', tono: 'revision' },
};

/** Orden del avance que ve el pasajero (ASIGNADO cuenta como «buscando»: el conductor aún no acepta). */
const ORDEN: EstadoViaje[] = ['SOLICITADO', 'ACEPTADO', 'EN_CAMINO', 'EN_ZONA', 'PASAJERO_A_BORDO', 'FINALIZADO'];

function alcanzado(estado: EstadoViaje): number {
  if (estado === 'PENDIENTE_CONFIRMACION') return -1;
  if (estado === 'ASIGNADO') return 0;
  return ORDEN.indexOf(estado);
}

/** Pasos de la línea de tiempo con su estado y la hora en que ocurrieron. */
export function pasosDelViaje(viaje: TuViaje): PasoLinea[] {
  const desdeAeropuerto = viaje.sentido === 'DESDE_AEROPUERTO';
  const titulos: Record<string, string> = {
    SOLICITADO: 'Pedido recibido',
    ACEPTADO: 'Conductor asignado',
    EN_CAMINO: desdeAeropuerto ? 'En camino al aeropuerto' : 'En camino a buscarte',
    EN_ZONA: desdeAeropuerto ? 'Esperándote en salida' : 'Te espera en el punto de recogida',
    PASAJERO_A_BORDO: 'A bordo',
    FINALIZADO: 'Viaje finalizado',
  };
  const hora = (estado: string) => {
    const paso = [...viaje.pasos].reverse().find((p) => p.estado === estado);
    return paso ? formatearFechaHora(paso.creado_en) : undefined;
  };
  const llegado = alcanzado(viaje.estado ?? 'SOLICITADO');
  return ORDEN.map((estado, i) => {
    let detalle = hora(estado);
    if (estado === 'SOLICITADO' && llegado === -1) detalle = 'Confírmalo respondiendo el WhatsApp';
    if (estado === 'ACEPTADO' && llegado >= 1 && viaje.conductor) detalle = viaje.conductor.nombre;
    if (estado === 'ACEPTADO' && llegado === 0) detalle = 'Buscando tu conductor';
    return {
      titulo: titulos[estado],
      detalle,
      estado: i <= llegado ? 'hecho' : i === llegado + 1 ? 'actual' : 'pendiente',
    };
  });
}

/** HU-44: los viajes terminados van en «Anteriores». */
export function esAnterior(estado?: EstadoViaje): boolean {
  return estado === 'FINALIZADO' || estado === 'CANCELADO';
}

/** «SCL → Hotel Cumbres»: el aeropuerto como SCL y de cada dirección lo que va antes de la primera coma. */
export function tramo(viaje: { sentido?: string; origen_dir: string; destino_dir: string }): string {
  const corta = (direccion: string) => direccion.split(',')[0].trim();
  const origen = viaje.sentido === 'DESDE_AEROPUERTO' ? 'SCL' : corta(viaje.origen_dir);
  const destino = viaje.sentido === 'HACIA_AEROPUERTO' ? 'SCL' : corta(viaje.destino_dir);
  return `${origen} → ${destino}`;
}

/** HU-44 (RN-09): solo sin conductor asignado se cancela desde la cuenta; si no, el texto para la central. */
export function textoDeCancelacion(viaje: { estado?: EstadoViaje; cancelable: boolean }): string | null {
  if (viaje.cancelable) return null;
  if (viaje.estado === 'FINALIZADO' || viaje.estado === 'CANCELADO') return null;
  return 'Para cancelar, contacta a la central.';
}
