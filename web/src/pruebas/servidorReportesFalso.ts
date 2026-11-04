/** /api/reportes/ falso, montado sobre el servidor de auth falso. Las demás rutas siguen al manejador anterior. */

import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

const COLUMNAS_LIQUIDACION = [
  { clave: 'dia', titulo: 'Día', tipo: 'fecha' },
  { clave: 'conductor', titulo: 'Conductor', tipo: 'texto' },
  { clave: 'viajes', titulo: 'Viajes', tipo: 'entero' },
  { clave: 'total', titulo: 'Total', tipo: 'pesos' },
  { clave: 'cierres_forzados', titulo: 'Cierres forzados', tipo: 'entero' },
];

export const LIQUIDACION = {
  columnas: COLUMNAS_LIQUIDACION,
  filas: [{ dia: '2026-07-15', conductor: 'Ana Conductora', viajes: 2, total: 13000, cierres_forzados: 1 }],
  totales: { conductor: 'Total', viajes: 2, total: 13000, cierres_forzados: 1 },
  count: 1,
  next: null,
  previous: null,
};

export const CANCELACIONES = {
  columnas: [
    { clave: 'origen', titulo: 'Origen', tipo: 'texto' },
    { clave: 'cantidad', titulo: 'Cancelaciones', tipo: 'entero' },
    { clave: 'tasa', titulo: 'Tasa sobre las reservas', tipo: 'porcentaje' },
  ],
  filas: [{ origen: 'Pasajero', cantidad: 2, tasa: 12.5 }],
  totales: { origen: 'Total, de 16 reservas', cantidad: 2, tasa: 12.5 },
  count: 1,
  next: null,
  previous: null,
};

export class ServidorReportesFalso {
  /** Consultas recibidas: «tipo?parámetros». */
  consultas: string[] = [];
  descargas: string[] = [];
  /** Retiene las respuestas de los reportes hasta que se resuelva. */
  espera: Promise<void> = Promise.resolve();
  reportes: Record<string, unknown> = { liquidacion: LIQUIDACION, cancelaciones: CANCELACIONES };
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
    if (!url.pathname.startsWith('/api/reportes/')) return this.anterior!(peticion, url);
    const programada = this.programadas.get(url.pathname)?.shift();
    if (programada) return programada;
    if (url.pathname === '/api/reportes/opciones/') {
      return { estado: 200, cuerpo: { conductores: [{ id: 3, nombre: 'Ana Conductora' }], convenios: [{ id: 9, nombre: 'Minera Norte' }] } };
    }
    const [, , , tipo, csv] = url.pathname.split('/');
    if (csv === 'csv') {
      this.descargas.push(`${tipo}?${url.searchParams}`);
      return { estado: 200, cuerpo: { csv: true } };
    }
    this.consultas.push(`${tipo}?${url.searchParams}`);
    await this.espera;
    const reporte = this.reportes[tipo];
    return reporte ? { estado: 200, cuerpo: reporte } : { estado: 200, cuerpo: { ...LIQUIDACION, filas: [], count: 0 } };
  }
}
