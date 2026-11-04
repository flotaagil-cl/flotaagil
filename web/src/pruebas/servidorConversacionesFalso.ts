/** /api/conversaciones/ falso, montado sobre el servidor de auth falso. Las demás rutas siguen al manejador anterior. */

import type { components } from '../api/esquema';
import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

type Detalle = components['schemas']['ConversacionDetalle'];

export function conversacionDePrueba(cambios: Partial<Detalle> = {}): Detalle {
  return {
    id: 5,
    nombre: 'Ana Pérez',
    telefono: '+56900009001',
    ultimo_mensaje: '¿Viene pronto?',
    ultima_direccion: 'ENTRANTE',
    ultimo_en: '2026-07-15T12:00:00Z',
    ventana_hasta: '2026-07-16T12:00:00Z',
    dentro_ventana: true,
    reserva: { id: 8, estado: 'EN_CAMINO' },
    mensajes: [
      { id: 1, direccion: 'ENTRANTE', tipo: 'SESION', cuerpo: '¿Viene pronto?', estado_entrega: 'DELIVERED', usuario: null, viaje: 8, creado_en: '2026-07-15T12:00:00Z' },
    ],
    ...cambios,
  };
}

export class ServidorConversacionesFalso {
  conversaciones: Detalle[] = [];
  cuerpos: unknown[] = [];
  private programadas = new Map<string, Respuesta[]>();
  private readonly anterior: ServidorAuthFalso['api'];

  constructor(auth: ServidorAuthFalso) {
    this.anterior = auth.api;
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  siguiente(ruta: string, respuesta: Respuesta) {
    this.programadas.set(ruta, [...(this.programadas.get(ruta) ?? []), respuesta]);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    if (!url.pathname.startsWith('/api/conversaciones/')) return this.anterior!(peticion, url);
    const ruta = `${peticion.method} ${url.pathname}`;
    const texto = peticion.method === 'GET' ? '' : await peticion.text();
    if (texto) this.cuerpos.push(JSON.parse(texto));
    const programada = this.programadas.get(ruta)?.shift();
    if (programada) return programada;
    if (ruta === 'GET /api/conversaciones/') {
      const filas = this.conversaciones.map((c) => ({
        id: c.id,
        nombre: c.nombre,
        telefono: c.telefono,
        ultimo_mensaje: c.ultimo_mensaje,
        ultima_direccion: c.ultima_direccion,
        ultimo_en: c.ultimo_en,
        ventana_hasta: c.ventana_hasta,
        dentro_ventana: c.dentro_ventana,
        reserva: c.reserva,
      }));
      return { estado: 200, cuerpo: { count: filas.length, next: null, previous: null, results: filas } };
    }
    const detalle = /^\/api\/conversaciones\/(\d+)\/(mensajes\/)?$/.exec(url.pathname);
    const conversacion = detalle && this.conversaciones.find((c) => c.id === Number(detalle[1]));
    if (!conversacion) return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
    if (detalle[2]) {
      const mensaje = {
        id: conversacion.mensajes.length + 1,
        direccion: 'SALIENTE' as const,
        tipo: 'SESION' as const,
        cuerpo: (JSON.parse(texto) as { texto: string }).texto,
        estado_entrega: 'QUEUED' as const,
        usuario: 'Diego Despacho',
        viaje: 8,
        creado_en: '2026-07-15T12:05:00Z',
      };
      conversacion.mensajes.push(mensaje);
      return { estado: 201, cuerpo: mensaje };
    }
    return { estado: 200, cuerpo: conversacion };
  }
}
