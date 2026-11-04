/**
 * /api/viajes/ falso, montado sobre el servidor de auth falso (mismo `fetch`, mismo access). Imita lo que la
 * interfaz usa del backend: listado paginado de a 25 (filtra por estado; el resto de la query solo se
 * registra en `servidor.urls` para revisarla), detalle con historial, crear (201), editar (409 fuera de
 * PENDIENTE_CONFIRMACION y SOLICITADO) y cancelar (409 fuera de los cancelables). `siguiente` programa la
 * próxima respuesta de una ruta (p. ej. un 400 con el formato de DRF). Los datos se tipan con el esquema
 * generado: si el contrato cambia, no compilan.
 */

import type { components } from '../api/esquema';
import type { Candidato, EstadoViaje, ViajeCrear, ViajeDetalle, ViajeEditar } from '../reservas/api';
import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

const EDITABLES: EstadoViaje[] = ['PENDIENTE_CONFIRMACION', 'SOLICITADO'];
const CANCELABLES: EstadoViaje[] = ['PENDIENTE_CONFIRMACION', 'SOLICITADO', 'ACEPTADO', 'EN_CAMINO', 'EN_ZONA'];

type Historial = components['schemas']['Historial'];

export type AlertaDePrueba = components['schemas']['AlertaVuelo'];

let siguienteId = 100;

/** Reserva completa con valores sintéticos; `cambios` reemplaza lo que haga falta. */
export function viajeDePrueba(cambios: Partial<ViajeDetalle> = {}): ViajeDetalle {
  const estado = cambios.estado ?? 'SOLICITADO';
  const id = cambios.id ?? ++siguienteId;
  return {
    id,
    estado,
    canal: 'TELEFONO',
    sentido: 'URBANO',
    pasajero: { id: 1, nombre: 'Pía Pasajera', telefono: '+56900000001' },
    origen: { direccion: 'Av. Siempre Viva 123', lat: -33.44, lon: -70.65 },
    destino: { direccion: 'Calle Falsa 456', lat: -33.42, lon: -70.6 },
    recogida_en: '2026-11-02T13:00:00Z',
    tarifa: null,
    conductor: null,
    vehiculo: null,
    convenio: null,
    vuelo: null,
    motivo_cancelacion: null,
    origen_cancelacion: null,
    creado_en: '2026-10-30T12:00:00Z',
    editable: EDITABLES.includes(estado),
    cancelable: CANCELABLES.includes(estado),
    calificacion: null,
    alerta_vuelo: null,
    cierre_forzado: null,
    historial: [
      { estado_anterior: null, estado_nuevo: 'SOLICITADO', actor: 'DESPACHADOR', usuario: 'Diego Despacho', creado_en: '2026-10-30T12:00:00Z' },
    ],
    ...cambios,
  };
}

/** El listado no trae el historial. */
function resumen(viaje: ViajeDetalle): Omit<ViajeDetalle, 'historial'> {
  return Object.fromEntries(Object.entries(viaje).filter(([clave]) => clave !== 'historial')) as Omit<ViajeDetalle, 'historial'>;
}

export class ServidorViajesFalso {
  viajes: ViajeDetalle[] = [];
  /** Alertas de vuelo sin atender (HU-28). */
  alertas: AlertaDePrueba[] = [];
  /** Conductores disponibles que devuelve /candidatos/ (HU-14). */
  candidatos: Candidato[] = [];
  /** Respuesta de /api/indicadores/ (HU-01). */
  indicadores: unknown = { fecha: '2026-07-15', reservas: { total: 0, por_estado: [] }, vehiculos: { en_linea: 0, en_linea_con_senal: 0, en_linea_sin_senal: 0, fuera_de_linea: 0 } };
  /** Cuerpos recibidos, por ruta («POST /api/viajes/», «PATCH /api/viajes/7/»…). */
  cuerpos: { ruta: string; cuerpo: unknown }[] = [];
  private programadas = new Map<string, Respuesta[]>();

  constructor(readonly auth: ServidorAuthFalso) {
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  agregar(...viajes: ViajeDetalle[]): ViajeDetalle[] {
    this.viajes.push(...viajes);
    return viajes;
  }

  /** La próxima petición a esa ruta («PATCH /api/viajes/7/») responde esto, sin tocar los datos. */
  siguiente(ruta: string, respuesta: Respuesta) {
    this.programadas.set(ruta, [...(this.programadas.get(ruta) ?? []), respuesta]);
  }

  /** Cambia el estado de una reserva «por fuera» (otro despachador, el conductor…). */
  cambiarEstado(id: number, estado: EstadoViaje) {
    const viaje = this.buscar(id)!;
    Object.assign(viaje, { estado, editable: EDITABLES.includes(estado), cancelable: CANCELABLES.includes(estado) });
  }

  buscar(id: number): ViajeDetalle | undefined {
    return this.viajes.find((viaje) => viaje.id === id);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    const ruta = `${peticion.method} ${url.pathname}`;
    const texto = peticion.method === 'GET' ? '' : await peticion.text();
    const cuerpo = texto ? JSON.parse(texto) : undefined;
    if (cuerpo !== undefined) this.cuerpos.push({ ruta, cuerpo });
    const programada = this.programadas.get(ruta)?.shift();
    if (programada) return programada;

    if (ruta === 'GET /api/indicadores/') return { estado: 200, cuerpo: this.indicadores };
    if (ruta === 'GET /api/alertas/') {
      return { estado: 200, cuerpo: { count: this.alertas.length, next: null, previous: null, results: this.alertas } };
    }
    const atender = /^POST \/api\/alertas\/(\d+)\/atender\/$/.exec(ruta);
    if (atender) {
      this.alertas = this.alertas.filter((a) => a.id !== Number(atender[1]));
      return { estado: 200, cuerpo: {} };
    }
    if (ruta === 'GET /api/viajes/') return this.listar(url);
    if (ruta === 'POST /api/viajes/') return this.crear(cuerpo as ViajeCrear);
    const detalle = /^\/api\/viajes\/(\d+)\/(?:(cancelar|asignar|candidatos|confirmar-recogida|descartar-recogida|forzar-cierre)\/)?$/.exec(url.pathname);
    const viaje = detalle && this.buscar(Number(detalle[1]));
    if (!viaje) return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
    if (detalle[2] === 'candidatos') return { estado: 200, cuerpo: this.candidatos };
    if (detalle[2] === 'forzar-cierre') {
      const { accion, motivo } = cuerpo as { accion: string; motivo: string };
      const anula = accion === 'ANULAR';
      Object.assign(viaje, {
        estado: anula ? 'CANCELADO' : 'FINALIZADO',
        cierre_forzado: { accion: anula ? 'ANULACION_FORZADA' : 'CIERRE_FORZADO', motivo, usuario: 'Diego Despacho', creado_en: '2026-07-15T12:00:00Z' },
      });
      return { estado: 200, cuerpo: viaje };
    }
    if (detalle[2] === 'confirmar-recogida' || detalle[2] === 'descartar-recogida') {
      const propuesta = (cuerpo as { recogida_propuesta: string }).recogida_propuesta;
      if (detalle[2] === 'confirmar-recogida') viaje.recogida_en = propuesta;
      Object.assign(viaje, { vuelo: { ...viaje.vuelo!, recogida_propuesta: null, propuesta_en: null } });
      return { estado: 200, cuerpo: viaje };
    }
    if (detalle[2] === 'asignar') return this.asignar(viaje, (cuerpo as { conductor: number }).conductor);
    if (detalle[2] && peticion.method === 'POST') return this.cancelar(viaje, (cuerpo as { motivo: string }).motivo);
    if (peticion.method === 'PATCH') return this.editar(viaje, cuerpo as ViajeEditar);
    return { estado: 200, cuerpo: viaje };
  }

  private listar(url: URL): Respuesta {
    const estados = url.searchParams.getAll('estado');
    const filtrados = estados.length ? this.viajes.filter((v) => estados.includes(v.estado!)) : this.viajes;
    const pagina = Number(url.searchParams.get('page') ?? 1);
    const paginas = Math.max(1, Math.ceil(filtrados.length / 25));
    if (pagina > paginas) return { estado: 404, cuerpo: { detail: 'Página inválida.' } };
    const conPagina = (n: number) => {
      const otra = new URL(url);
      otra.searchParams.set('page', String(n));
      return otra.toString();
    };
    return {
      estado: 200,
      cuerpo: {
        count: filtrados.length,
        next: pagina < paginas ? conPagina(pagina + 1) : null,
        previous: pagina > 1 ? conPagina(pagina - 1) : null,
        results: filtrados.slice((pagina - 1) * 25, pagina * 25).map(resumen),
      },
    };
  }

  private crear(datos: ViajeCrear): Respuesta {
    const viaje = viajeDePrueba({
      canal: datos.canal ?? 'TELEFONO',
      sentido: datos.sentido ?? 'URBANO',
      pasajero: { id: 9, ...datos.pasajero },
      origen: { direccion: datos.origen_dir, lat: -33.4, lon: -70.6 },
      destino: { direccion: datos.destino_dir, lat: -33.4, lon: -70.6 },
      recogida_en: datos.recogida_en,
      vuelo: datos.vuelo
        ? { numero: datos.vuelo.numero, hora_programada: datos.vuelo.hora_programada, fecha: datos.vuelo.hora_programada.slice(0, 10), hora_estimada: null, estado_vuelo: 'PROGRAMADO' }
        : null,
    });
    this.viajes.push(viaje);
    return { estado: 201, cuerpo: viaje };
  }

  private editar(viaje: ViajeDetalle, cambios: ViajeEditar): Respuesta {
    if (!viaje.editable) {
      return { estado: 409, cuerpo: { detail: 'Solo se puede editar una reserva pendiente de confirmación o solicitada (antes del despacho).' } };
    }
    // Los campos de solo lectura del esquema (origen, destino, vuelo) se reemplazan en una copia.
    const editado: ViajeDetalle = {
      ...viaje,
      sentido: cambios.sentido ?? viaje.sentido,
      origen: cambios.origen_dir ? { ...viaje.origen, direccion: cambios.origen_dir } : viaje.origen,
      destino: cambios.destino_dir ? { ...viaje.destino, direccion: cambios.destino_dir } : viaje.destino,
      recogida_en: cambios.recogida_en ?? viaje.recogida_en,
    };
    const sentido = editado.sentido;
    const vuelo =
      cambios.vuelo !== undefined || sentido !== 'DESDE_AEROPUERTO'
        ? cambios.vuelo
          ? { numero: cambios.vuelo.numero, hora_programada: cambios.vuelo.hora_programada, fecha: cambios.vuelo.hora_programada.slice(0, 10), hora_estimada: null, estado_vuelo: 'PROGRAMADO' as const }
          : null
        : viaje.vuelo;
    const final = { ...editado, vuelo };
    this.viajes[this.viajes.indexOf(viaje)] = final;
    return { estado: 200, cuerpo: final };
  }

  private asignar(viaje: ViajeDetalle, conductor: number): Respuesta {
    const elegido = this.candidatos.find((c) => c.id === conductor);
    if (viaje.estado !== 'SOLICITADO' || !elegido) {
      return { estado: 409, cuerpo: { detail: 'No se puede asignar este viaje ahora.', code: 'asignacion_no_permitida' } };
    }
    Object.assign(viaje, {
      estado: 'ASIGNADO',
      editable: false,
      cancelable: false,
      conductor: { id: elegido.id, nombre: elegido.nombre },
      vehiculo: { id: 1, patente: elegido.patente },
    });
    return { estado: 200, cuerpo: viaje };
  }

  private cancelar(viaje: ViajeDetalle, motivo: string): Respuesta {
    if (!viaje.cancelable) {
      return { estado: 409, cuerpo: { detail: `Una reserva en estado ${viaje.estado} no se puede cancelar desde aquí.` } };
    }
    const anterior = viaje.estado!;
    const cambio: Historial = { estado_anterior: anterior, estado_nuevo: 'CANCELADO', actor: 'DESPACHADOR', usuario: 'Diego Despacho', creado_en: '2026-10-30T13:00:00Z' };
    Object.assign(viaje, {
      estado: 'CANCELADO',
      editable: false,
      cancelable: false,
      motivo_cancelacion: motivo.trim(),
      origen_cancelacion: 'DESPACHADOR',
      historial: [...viaje.historial, cambio],
    });
    return { estado: 200, cuerpo: viaje };
  }
}
