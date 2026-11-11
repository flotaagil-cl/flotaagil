/**
 * HU-39: pedido del pasajero con cuenta en tres tipos. Arma el cuerpo de `POST /api/mi-cuenta/solicitudes/` y
 * valida antes de enviar; las reglas finales (anticipación, capacidad, vuelo) las aplica el backend.
 */

import type { components } from '../api/esquema';
import { aIso, instanteDeCampo, paredDe } from '../hora/hora';

export type EmpresaPublica = components['schemas']['EmpresaPublica'];
export type CuerpoPedido = components['schemas']['SolicitudCuentaRequest'];
export type TipoVuelo = components['schemas']['TipoVueloEnum'];

export type TipoPedido = 'desde-aeropuerto' | 'al-aeropuerto' | 'en-la-ciudad';

export const AEROPUERTO = 'Aeropuerto de Santiago (SCL)';

export const TIPOS: { id: TipoPedido; titulo: string; detalle: string }[] = [
  { id: 'desde-aeropuerto', titulo: 'Desde el aeropuerto', detalle: 'Seguimos tu vuelo por ti' },
  { id: 'al-aeropuerto', titulo: 'Al aeropuerto', detalle: 'Te recogemos y llegas a tiempo' },
  { id: 'en-la-ciudad', titulo: 'En la ciudad', detalle: 'Traslados dentro de Santiago' },
];

export function esTipo(valor: string | undefined): valor is TipoPedido {
  return TIPOS.some((t) => t.id === valor);
}

export interface ValoresPedido {
  origen: string;
  destino: string;
  pasajeros: number;
  maletas: number;
  /** Desde el aeropuerto. */
  vueloNumero: string;
  vueloFecha: string;
  /** Solo si la API de vuelos no respondió y el backend pidió la hora. */
  vueloHora: string;
  /** Al aeropuerto. */
  salidaFecha: string;
  salidaHora: string;
  salidaTipo: TipoVuelo;
  /** Recogida editada a mano (al aeropuerto con «Cambiar», o en la ciudad programado). */
  recogidaFecha: string;
  recogidaHora: string;
  cambiarRecogida: boolean;
  /** En la ciudad: «Ahora» = lo antes posible (ahora + la anticipación mínima, DC-10). */
  ahora: boolean;
}

export const VALORES_INICIALES: ValoresPedido = {
  origen: '',
  destino: '',
  pasajeros: 1,
  maletas: 0,
  vueloNumero: '',
  vueloFecha: '',
  vueloHora: '',
  salidaFecha: '',
  salidaHora: '',
  salidaTipo: 'INTERNACIONAL',
  recogidaFecha: '',
  recogidaHora: '',
  cambiarRecogida: false,
  ahora: true,
};

export type Errores = Partial<Record<keyof ValoresPedido | 'general', string>>;

const VUELO_IATA = /^[A-Z0-9]{2}\s?\d{1,4}[A-Z]?$/;

function instante(fecha: string, hora: string): number | null {
  if (!fecha || !hora) return null;
  const r = instanteDeCampo({ pared: `${fecha}T${hora}`, ocurrencia: 'primera' });
  return r.ok ? r.instante : null;
}

/** Al aeropuerto: hora del vuelo menos la antelación de su tipo (DC-42). null si falta la hora del vuelo. */
export function recogidaSugerida(v: ValoresPedido, empresa: EmpresaPublica): number | null {
  const salida = instante(v.salidaFecha, v.salidaHora);
  if (salida === null) return null;
  const antelacion = v.salidaTipo === 'INTERNACIONAL' ? empresa.antelacion_vuelo_internacional_min : empresa.antelacion_vuelo_nacional_min;
  return salida - antelacion * 60_000;
}

/** «05:40» en hora de Chile. */
export function horaDe(instanteMs: number): string {
  const p = paredDe(instanteMs);
  return `${String(p.hora).padStart(2, '0')}:${String(p.minuto).padStart(2, '0')}`;
}

/** «3 horas» / «2 horas» / «90 minutos». */
export function textoAntelacion(minutos: number): string {
  return minutos % 60 === 0 ? `${minutos / 60} ${minutos === 60 ? 'hora' : 'horas'}` : `${minutos} minutos`;
}

/** Valida y arma el cuerpo. Los errores van por campo, con el texto que ve el pasajero. */
export function armarPedido(tipo: TipoPedido, v: ValoresPedido, empresa: EmpresaPublica): { cuerpo: CuerpoPedido } | { errores: Errores } {
  const errores: Errores = {};
  const maximo = empresa.capacidad_maxima;
  if (v.pasajeros > maximo) errores.pasajeros = `Podemos llevar hasta ${maximo} pasajeros en un vehículo.`;
  // DC-44: el pedido no acepta nada; la cuenta aceptó el aviso una vez al crearse.
  const base = { pasajeros: v.pasajeros, maletas: v.maletas };

  if (tipo === 'desde-aeropuerto') {
    const numero = v.vueloNumero.trim().toUpperCase();
    if (!numero) errores.vueloNumero = 'Ingresa el número de vuelo.';
    else if (!VUELO_IATA.test(numero)) errores.vueloNumero = 'Revisa el número: por ejemplo, LA 845.';
    if (!v.vueloFecha) errores.vueloFecha = 'Indica la fecha del vuelo.';
    if (!v.destino.trim()) errores.destino = 'Ingresa la dirección de destino.';
    let llegada: string | undefined;
    if (v.vueloHora) {
      const ms = instante(v.vueloFecha, v.vueloHora);
      if (ms === null) errores.vueloHora = 'Ingresa una hora válida.';
      else llegada = aIso(ms);
    }
    if (Object.keys(errores).length) return { errores };
    return {
      cuerpo: {
        ...base,
        sentido: 'DESDE_AEROPUERTO',
        origen_dir: AEROPUERTO,
        destino_dir: v.destino.trim(),
        vuelo: llegada ? { numero, hora_llegada: llegada } : { numero, fecha: v.vueloFecha },
      },
    };
  }

  if (tipo === 'al-aeropuerto') {
    if (!v.origen.trim()) errores.origen = 'Ingresa la dirección de recogida.';
    if (!v.salidaFecha) errores.salidaFecha = 'Indica la fecha del vuelo.';
    if (!v.salidaHora) errores.salidaHora = 'Indica la hora de salida.';
    const salida = instante(v.salidaFecha, v.salidaHora);
    if (v.salidaFecha && v.salidaHora && salida === null) errores.salidaHora = 'Ingresa una hora válida.';
    let recogida: string | undefined;
    if (v.cambiarRecogida) {
      const ms = instante(v.recogidaFecha, v.recogidaHora);
      if (ms === null) errores.recogidaHora = 'Indica la fecha y hora de recogida.';
      else recogida = aIso(ms);
    }
    if (Object.keys(errores).length || salida === null) return { errores };
    return {
      cuerpo: {
        ...base,
        sentido: 'HACIA_AEROPUERTO',
        origen_dir: v.origen.trim(),
        destino_dir: AEROPUERTO,
        vuelo_salida: { hora: aIso(salida), tipo: v.salidaTipo },
        ...(recogida && { recogida_en: recogida }),
      },
    };
  }

  if (!v.origen.trim()) errores.origen = 'Ingresa la dirección de origen.';
  if (!v.destino.trim()) errores.destino = 'Ingresa la dirección de destino.';
  let recogida: string | undefined;
  if (!v.ahora) {
    const ms = instante(v.recogidaFecha, v.recogidaHora);
    if (ms === null) errores.recogidaHora = 'Indica la fecha y hora de recogida.';
    else recogida = aIso(ms);
  }
  if (Object.keys(errores).length) return { errores };
  return {
    cuerpo: {
      ...base,
      sentido: 'URBANO',
      origen_dir: v.origen.trim(),
      destino_dir: v.destino.trim(),
      ...(v.ahora ? { lo_antes_posible: true } : { recogida_en: recogida }),
    },
  };
}

/** Errores 400 del backend llevados a los campos del formulario. */
export function erroresDelServidor(cuerpo: unknown): Errores {
  const c = (cuerpo ?? {}) as Record<string, unknown>;
  const primero = (valor: unknown): string | undefined => (Array.isArray(valor) ? String(valor[0]) : typeof valor === 'string' ? valor : undefined);
  const vuelo = (c.vuelo ?? {}) as Record<string, unknown>;
  const salida = (c.vuelo_salida ?? {}) as Record<string, unknown>;
  const errores: Errores = {
    origen: primero(c.origen_dir),
    destino: primero(c.destino_dir),
    pasajeros: primero(c.pasajeros),
    maletas: primero(c.maletas),
    vueloNumero: primero(vuelo.numero) ?? (typeof c.vuelo === 'string' ? c.vuelo : undefined),
    vueloFecha: primero(vuelo.fecha),
    vueloHora: primero(vuelo.hora_llegada),
    salidaHora: primero(salida.hora) ?? (typeof c.vuelo_salida === 'string' ? c.vuelo_salida : undefined),
    recogidaHora: primero(c.recogida_en),
  };
  const limpios = Object.fromEntries(Object.entries(errores).filter(([, valor]) => valor)) as Errores;
  return Object.keys(limpios).length ? limpios : { general: primero(c.detail) ?? 'Revisa los datos del pedido.' };
}
