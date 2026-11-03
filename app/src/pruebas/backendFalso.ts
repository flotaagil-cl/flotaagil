/**
 * Backend falso para las pruebas de la app: login, refresh con rotación y lista negra, logout, cambio de
 * contraseña, `yo` y posiciones (idempotentes por instante). `vencerAccess()` invalida los access vigentes como si
 * hubieran pasado sus 15 min; `sinRed` hace fallar las peticiones como sin señal.
 */

import type { Usuario } from '../sesion/sesion';

export const USUARIO: Usuario = {
  id: 7,
  nombre: 'Carla Conductora',
  email: 'conductor1@andes.example',
  rol: 'CONDUCTOR',
  debe_cambiar_password: false,
  empresa: { id: 1, razon_social: 'Transportes Andes Demo SpA', slug: 'transportes-andes' },
};

function json(estado: number, cuerpo?: unknown): Response {
  return new Response(cuerpo === undefined ? null : JSON.stringify(cuerpo), {
    status: estado,
    headers: { 'Content-Type': 'application/json' },
  });
}

export class BackendFalso {
  password = 'clave';
  debeCambiar = false;
  enTurno = true;
  sinRed = false;
  /** Rutas cuyas próximas N respuestas son un error de red (p. ej. el refresh con la app en segundo plano). */
  cortes = new Map<string, number>();
  llamadas: string[] = [];
  posiciones = new Map<string, { lat: number; lon: number }>();
  private accessVigentes = new Set<string>();
  private refreshVigentes = new Set<string>();
  private contador = 0;

  emitir(): { access: string; refresh: string } {
    const access = `A${++this.contador}`;
    const refresh = `R${++this.contador}`;
    this.accessVigentes.add(access);
    this.refreshVigentes.add(refresh);
    return { access, refresh };
  }

  vencerAccess() {
    this.accessVigentes.clear();
  }

  get refreshActivos(): number {
    return this.refreshVigentes.size;
  }

  http = async (url: string, init: RequestInit): Promise<Response> => {
    const ruta = `${init.method ?? 'GET'} ${new URL(url).pathname}`;
    this.llamadas.push(ruta);
    const cortes = this.cortes.get(ruta) ?? 0;
    if (this.sinRed || cortes > 0) {
      if (cortes) this.cortes.set(ruta, cortes - 1);
      throw new TypeError('Failed to fetch');
    }
    const cuerpo = init.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
    const headers = new Headers(init.headers);
    const access = headers.get('Authorization')?.replace('Bearer ', '') ?? '';

    switch (ruta) {
      case 'POST /api/auth/app/token/':
        if (cuerpo.password !== this.password) return json(401, { detail: 'Correo o contraseña incorrectos.', code: 'credenciales_invalidas' });
        return json(200, { ...this.emitir(), usuario: { ...USUARIO, debe_cambiar_password: this.debeCambiar } });
      case 'POST /api/auth/app/refresh/': {
        const refresh = String(cuerpo.refresh);
        if (!this.refreshVigentes.delete(refresh)) return json(401, { detail: 'La sesión no es válida o expiró.', code: 'sesion_invalida' });
        return json(200, this.emitir());
      }
      case 'POST /api/auth/app/logout/':
        this.refreshVigentes.delete(String(cuerpo.refresh));
        return json(204);
    }
    if (!this.accessVigentes.has(access)) return json(401, { detail: 'Token inválido.', code: 'token_not_valid' });
    if (ruta === 'POST /api/auth/password/') {
      if (cuerpo.password_actual !== this.password) return json(400, { password_actual: ['La contraseña actual no es correcta.'] });
      this.password = String(cuerpo.password_nueva);
      this.debeCambiar = false;
      this.accessVigentes.clear();
      this.refreshVigentes.clear();
      return json(200, this.emitir());
    }
    if (ruta === 'GET /api/auth/yo/') return json(200, { ...USUARIO, debe_cambiar_password: this.debeCambiar });
    if (this.debeCambiar) return json(403, { detail: 'Debes cambiar tu contraseña temporal antes de continuar.', code: 'cambio_password_requerido' });
    if (ruta === 'POST /api/app/posiciones/') {
      if (!this.enTurno) return json(409, { detail: 'Fuera de turno.', code: 'fuera_de_turno' });
      const lote = cuerpo.posiciones as { lat: number; lon: number; registrada_en: string }[];
      let recibidas = 0;
      for (const p of lote) {
        if (!this.posiciones.has(p.registrada_en)) recibidas += 1;
        this.posiciones.set(p.registrada_en, { lat: p.lat, lon: p.lon });
      }
      return json(201, { recibidas, repetidas: lote.length - recibidas, descartadas: 0 });
    }
    return json(404, { detail: 'No encontrado.', code: 'not_found' });
  };
}
