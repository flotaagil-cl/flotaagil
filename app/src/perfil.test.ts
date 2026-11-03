import { describe, expect, it } from 'vitest';
import { modoDeRastreo, type Perfil } from './perfil';

const base: Perfil = { id: 1, nombre: 'C', estado: 'DISPONIBLE', vehiculo_activo: null, consentimiento_gps_en: '2026-11-03T12:00:00Z', vehiculos: [] };

describe('modoDeRastreo (RN-18)', () => {
  it('solo en turno y con consentimiento', () => {
    expect(modoDeRastreo(base)).toBe('espera');
    expect(modoDeRastreo({ ...base, estado: 'EN_VIAJE' })).toBe('viaje');
    expect(modoDeRastreo({ ...base, estado: 'NO_DISPONIBLE' })).toBeNull();
    expect(modoDeRastreo({ ...base, consentimiento_gps_en: null })).toBeNull();
    expect(modoDeRastreo(null)).toBeNull();
  });
});
