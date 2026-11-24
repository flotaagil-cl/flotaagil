/**
 * Backend falso del portal público: GET /api/portal/{slug}/ y POST /api/portal/{slug}/registro-empresa/.
 *
 * Imita las respuestas del backend (404 de empresa inexistente, fallas al cargar) y permite programar la
 * próxima respuesta del registro. Cualquier llamada a /api/auth/ hace fallar la prueba: el portal no tiene
 * sesión. HU-46: el formulario de invitado de HU-19 ya no existe (CC-18), y con él su POST de solicitudes.
 */

import type { EmpresaPublica } from '../portal/api';

export const AHORA_PORTAL = Date.parse('2026-10-30T15:00:00Z'); // vie 30-10-2026 12:00 en Santiago

export const EMPRESA_PORTAL: EmpresaPublica = {
  razon_social: 'Transportes Andes Demo SpA',
  slug: 'transportes-andes',
  modulo_cuentas: true,
  anticipacion_minima_min: 30,
  expiracion_verificacion_min: 15,
  margen_nacional_min: 20,
  antelacion_vuelo_nacional_min: 120,
  antelacion_vuelo_internacional_min: 180,
  capacidad_maxima: 6,
  convenio_max_personas: 10,
  central: { telefono: null, whatsapp: null }, // HU-49
};

interface Programada {
  estado: number | 'red';
  cuerpo?: unknown;
}

export class ServidorPortalFalso {
  empresas: Record<string, EmpresaPublica> = { [EMPRESA_PORTAL.slug]: EMPRESA_PORTAL };
  llamadas: string[] = [];
  /** HU-34: registros de empresas recibidos. */
  registros: Record<string, string>[] = [];
  /** Llamadas prohibidas (p. ej. a /api/auth/): la prueba las revisa. */
  prohibidas: string[] = [];
  fallaEmpresa: number | 'red' | null = null;
  private programadas: Programada[] = [];

  constructor(readonly ahora = AHORA_PORTAL) {}

  /** El próximo registro responde esto (o falla por red). */
  siguiente(respuesta: Programada) {
    this.programadas.push(respuesta);
  }

  fetch = async (entrada: Request | string, init?: RequestInit): Promise<Response> => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const url = new URL(peticion.url);
    const ruta = `${peticion.method} ${url.pathname}`;
    this.llamadas.push(ruta);
    if (!url.pathname.startsWith('/api/portal/')) {
      this.prohibidas.push(ruta);
      throw new Error(`El portal no debe llamar a ${ruta}`);
    }
    const [, , , slug, recurso] = url.pathname.split('/');
    const empresa = this.empresas[slug];
    if (peticion.method === 'GET' && !recurso) {
      if (this.fallaEmpresa === 'red') throw new TypeError('Failed to fetch');
      if (this.fallaEmpresa) return json(this.fallaEmpresa, { detail: 'Error.' });
      return empresa ? json(200, empresa) : json(404, { detail: 'No encontrado.' });
    }
    if (recurso === 'registro-empresa') {
      const registro = (await peticion.json()) as Record<string, string>;
      this.registros.push(registro);
      const programada = this.programadas.shift();
      if (programada?.estado === 'red') throw new TypeError('Failed to fetch');
      if (programada) return json(programada.estado, programada.cuerpo ?? {});
      return json(201, { estado: 'EN_REVISION', mensaje: 'Recibimos el registro.' });
    }
    return json(404, { detail: 'No encontrado.' });
  };
}

function json(estado: number, cuerpo: unknown): Response {
  return new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });
}
