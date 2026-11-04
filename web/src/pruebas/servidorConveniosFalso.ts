/** /api/convenios/ falso, montado sobre el servidor de auth falso. Las demás rutas siguen al manejador anterior. */

import type { components } from '../api/esquema';
import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

type ConvenioDetalle = components['schemas']['ConvenioDetalle'];

let siguienteId = 700;

export function convenioDePrueba(cambios: Partial<ConvenioDetalle> = {}): ConvenioDetalle {
  return {
    id: cambios.id ?? ++siguienteId,
    cliente_nombre: 'Minera Sintética S.A.',
    cliente_rut: '76543210-3',
    activo: true,
    reservas: 0,
    token_link: 'tokenSintetico'.padEnd(43, 'x'),
    ...cambios,
  };
}

export class ServidorConveniosFalso {
  convenios: ConvenioDetalle[] = [];
  cuerpos: { ruta: string; cuerpo: unknown }[] = [];
  password = 'ClaveSintetica23';
  auditoria: components['schemas']['RegistroAuditoria'][] = [];
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
    if (!url.pathname.startsWith('/api/convenios/')) return this.anterior!(peticion, url);
    const ruta = `${peticion.method} ${url.pathname}`;
    const texto = peticion.method === 'GET' ? '' : await peticion.text();
    const cuerpo = texto ? (JSON.parse(texto) as Record<string, unknown>) : undefined;
    if (cuerpo) this.cuerpos.push({ ruta, cuerpo });
    const programada = this.programadas.get(ruta)?.shift();
    if (programada) return programada;

    if (ruta === 'GET /api/convenios/') {
      const activo = url.searchParams.get('activo');
      const q = url.searchParams.get('q')?.toLowerCase();
      const filas = this.convenios
        .filter((c) => activo === null || String(c.activo) === activo)
        .filter((c) => !q || c.cliente_nombre.toLowerCase().includes(q) || c.cliente_rut.includes(q))
        .map((c) => ({ id: c.id, cliente_nombre: c.cliente_nombre, cliente_rut: c.cliente_rut, activo: c.activo, reservas: c.reservas }));
      return { estado: 200, cuerpo: { count: filas.length, next: null, previous: null, results: filas } };
    }
    if (ruta === 'POST /api/convenios/') {
      const nuevo = convenioDePrueba(cuerpo as Partial<ConvenioDetalle>);
      this.convenios.push(nuevo);
      return { estado: 201, cuerpo: { ...nuevo, password: this.password } };
    }
    const detalle = /^\/api\/convenios\/(\d+)\/(rotar-password\/|auditoria\/)?$/.exec(url.pathname);
    const convenio = detalle && this.convenios.find((c) => c.id === Number(detalle[1]));
    if (!convenio) return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
    if (detalle[2] === 'auditoria/') {
      const pagina = Number(url.searchParams.get('page') ?? 1);
      const filas = this.auditoria.slice((pagina - 1) * 25, pagina * 25);
      return { estado: 200, cuerpo: { count: this.auditoria.length, next: this.auditoria.length > pagina * 25 ? 'x' : null, previous: pagina > 1 ? 'x' : null, results: filas } };
    }
    if (detalle[2]) {
      this.password = `${this.password}N`;
      this.auditoria.unshift({ id: this.auditoria.length + 1, accion: 'CAMBIO_CLAVE', usuario: 'Ana Admin', creado_en: '2026-07-15T12:00:00Z' });
      return { estado: 200, cuerpo: { password: this.password } };
    }
    if (peticion.method === 'PATCH') Object.assign(convenio, cuerpo);
    return { estado: 200, cuerpo: convenio };
  }
}
