/** /api/chat/ falso (CC-19), montado sobre el servidor de auth falso. Las demás rutas siguen al manejador anterior. */

import type { components } from '../api/esquema';
import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

type Conversacion = components['schemas']['ConversacionChat'];
type Mensaje = components['schemas']['MensajeChat'];
type Grupo = components['schemas']['Grupo'];
type Persona = components['schemas']['PersonaChat'];

const POR_PAGINA = 30;

export function conversacionChat(cambios: Partial<Conversacion> = {}): Conversacion {
  return {
    id: 1,
    tipo: 'CENTRAL',
    titulo: 'Pedro Soto',
    no_leidos: 1,
    ultimo: { texto: 'Voy en camino', autor: 'Pedro Soto', creado_en: '2026-11-17T12:00:00Z' },
    ultimo_mensaje_en: '2026-11-17T12:00:00Z',
    puede_gestionar: false,
    puede_borrar: false,
    ...cambios,
  };
}

export function mensajeChat(cambios: Partial<Mensaje> = {}): Mensaje {
  return { id: 1, conversacion: 1, texto: 'Voy en camino', rapida: 'EN_CAMINO', autor: 'Pedro Soto', propio: false, creado_en: '2026-11-17T12:00:00Z', ...cambios };
}

export class ServidorChatFalso {
  conversaciones: Conversacion[] = [conversacionChat()];
  mensajes = new Map<number, Mensaje[]>([[1, [mensajeChat()]]]);
  leidoPorOtros = 0;
  personal: Persona[] = [
    { id: 1, nombre: 'Ana Admin', rol: 'ADMINISTRADOR' },
    { id: 3, nombre: 'Carla Conductora', rol: 'CONDUCTOR' },
  ];
  grupos = new Map<number, Grupo>();
  /** «MÉTODO ruta» y cuerpo de cada petición que no es GET. */
  recibidas: { ruta: string; cuerpo: unknown }[] = [];
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
    if (!url.pathname.startsWith('/api/chat/')) return this.anterior!(peticion, url);
    const ruta = `${peticion.method} ${url.pathname}`;
    const texto = peticion.method === 'GET' ? '' : await peticion.text();
    const cuerpo = texto ? (JSON.parse(texto) as Record<string, unknown>) : null;
    if (peticion.method !== 'GET') this.recibidas.push({ ruta, cuerpo });
    const programada = this.programadas.get(ruta)?.shift();
    if (programada) return programada;

    if (ruta === 'GET /api/chat/conversaciones/') return { estado: 200, cuerpo: this.conversaciones };
    if (ruta === 'GET /api/chat/personal/') return { estado: 200, cuerpo: this.personal };
    if (ruta === 'GET /api/chat/moderacion/grupos/') return { estado: 200, cuerpo: [...this.grupos.values()] };
    if (ruta === 'POST /api/chat/directos/') {
      const persona = this.personal.find((p) => p.id === cuerpo?.usuario)!;
      const nueva = conversacionChat({ id: 50, tipo: 'DIRECTO', titulo: persona.nombre, no_leidos: 0, ultimo: null, ultimo_mensaje_en: null });
      this.conversaciones = [...this.conversaciones, nueva];
      this.mensajes.set(50, []);
      return { estado: 201, cuerpo: nueva };
    }
    if (ruta === 'POST /api/chat/grupos/') {
      const grupo: Grupo = { id: 60, nombre: String(cuerpo?.nombre), integrantes: [], creado_por: 'Diego Despacho', creado_en: '2026-11-17T12:00:00Z', ultimo_mensaje_en: null };
      this.grupos.set(60, grupo);
      this.conversaciones = [...this.conversaciones, conversacionChat({ id: 60, tipo: 'GRUPO', titulo: grupo.nombre, no_leidos: 0, ultimo: null, puede_gestionar: true, puede_borrar: true })];
      this.mensajes.set(60, []);
      return { estado: 201, cuerpo: grupo };
    }

    const hilo = /^\/api\/chat\/conversaciones\/(\d+)\/(mensajes|leido)\/$/.exec(url.pathname);
    if (hilo) {
      const id = Number(hilo[1]);
      const lista = this.mensajes.get(id);
      if (!lista) return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
      if (hilo[2] === 'leido') return { estado: 204 };
      if (peticion.method === 'POST') {
        const nuevo = mensajeChat({ id: 1000 + lista.length, conversacion: id, texto: String(cuerpo?.texto ?? ''), rapida: '', autor: 'Diego Despacho', propio: true });
        lista.push(nuevo);
        return { estado: 201, cuerpo: nuevo };
      }
      const antes = Number(url.searchParams.get('antes') ?? Infinity);
      const previos = lista.filter((m) => m.id < antes);
      return {
        estado: 200,
        cuerpo: { results: previos.slice(-POR_PAGINA), hay_mas: previos.length > POR_PAGINA, leido_por_otros_hasta: this.leidoPorOtros },
      };
    }

    const grupo = /^\/api\/chat\/grupos\/(\d+)\/(?:integrantes\/(\d+)\/)?$/.exec(url.pathname);
    if (grupo) {
      const actual = this.grupos.get(Number(grupo[1]));
      if (!actual) return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
      if (peticion.method === 'GET') return { estado: 200, cuerpo: actual };
      if (peticion.method === 'PATCH') {
        actual.nombre = String(cuerpo?.nombre);
        return { estado: 200, cuerpo: actual };
      }
      if (peticion.method === 'DELETE' && grupo[2]) {
        this.grupos.set(actual.id, { ...actual, integrantes: actual.integrantes.filter((i) => i.id !== Number(grupo[2])) });
        return { estado: 204 };
      }
      if (peticion.method === 'DELETE') {
        this.grupos.delete(actual.id);
        return { estado: 204 };
      }
    }
    return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
  }
}
