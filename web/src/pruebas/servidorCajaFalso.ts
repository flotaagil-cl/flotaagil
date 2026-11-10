/** /api/turnos/ falso (HU-31), montado sobre el servidor de auth falso. Las demás rutas siguen al anterior. */

import type { TurnoPorCerrar } from '../caja/api';
import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

export const TURNO_48: TurnoPorCerrar = {
  id: 7,
  conductor_id: 3,
  conductor: 'Ana Conductora',
  patente: 'ABCD12',
  hora_inicio: '2026-07-15T12:00:00Z',
  hora_termino: '2026-07-15T20:00:00Z',
  motivo_termino: 'CONDUCTOR',
  efectivo_registrado: 48000,
  viajes_finalizados: 4,
  con_viaje_en_ejecucion: false,
};

export class ServidorCajaFalso {
  turnos: TurnoPorCerrar[] = [TURNO_48];
  cierres: { id: number; cuerpo: { monto_rendido: number; observacion?: string } }[] = [];
  private programadas: Respuesta[] = [];
  private readonly anterior: ServidorAuthFalso['api'];

  constructor(auth: ServidorAuthFalso) {
    this.anterior = auth.api;
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  siguiente(respuesta: Respuesta) {
    this.programadas.push(respuesta);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    if (!url.pathname.startsWith('/api/turnos/')) return this.anterior!(peticion, url);
    if (url.pathname === '/api/turnos/por-cerrar/') return { estado: 200, cuerpo: this.turnos };
    const cierre = url.pathname.match(/^\/api\/turnos\/(\d+)\/cierre-caja\/$/);
    if (cierre && peticion.method === 'POST') {
      const id = Number(cierre[1]);
      const cuerpo = (await peticion.json()) as { monto_rendido: number; observacion?: string };
      this.cierres.push({ id, cuerpo });
      const programada = this.programadas.shift();
      if (programada) return programada;
      const turno = this.turnos.find((t) => t.id === id)!;
      this.turnos = this.turnos.filter((t) => t.id !== id);
      return {
        estado: 201,
        cuerpo: {
          id: 1,
          monto_registrado: turno.efectivo_registrado,
          monto_rendido: cuerpo.monto_rendido,
          diferencia: cuerpo.monto_rendido - turno.efectivo_registrado,
          observacion: cuerpo.observacion ?? null,
          responsable: 'Admin Andes',
          fecha_cierre: '2026-07-16T12:00:00Z',
        },
      };
    }
    return { estado: 404, cuerpo: { detail: 'No encontrado.' } };
  }
}
