import { describe, expect, it } from 'vitest';
import { avisoLicencia, diasHasta } from './etiquetas';
import {
  cuerpoEditarConductor,
  cuerpoEditarVehiculo,
  digitoVerificador,
  esquemaConductor,
  esquemaVehiculo,
  normalizarMovil,
  normalizarPatente,
  normalizarRut,
  rutValido,
} from './formularios';

describe('normalización', () => {
  it('patente, RUT y móvil como el backend', () => {
    expect(normalizarPatente(' ab-12.34 ')).toBe('AB1234');
    expect(normalizarRut('12.345.678-k')).toBe('12345678-K');
    expect(normalizarMovil('9 0000 1234')).toBe('+56900001234');
    expect(normalizarMovil('+56 9 0000-1234')).toBe('+56900001234');
    expect(normalizarMovil('22 123 4567')).toBe('221234567');
  });

  it('dígito verificador', () => {
    expect(digitoVerificador('12345678')).toBe('5');
    expect(digitoVerificador('15000103')).toBe('K');
    expect(rutValido('12345678-5')).toBe(true);
    expect(rutValido('12345678-9')).toBe(false);
    expect(rutValido('1234-5')).toBe(false);
  });
});

describe('esquemas', () => {
  it('vehículo: antigüedad máxima de 12 años y capacidad 1 a 7', () => {
    const esquema = esquemaVehiculo(2026);
    const base = { patente: 'BCDF10', marca_modelo: 'Kia Rio', anio: '2014', capacidad: '7' };
    expect(esquema.safeParse(base).success).toBe(true);
    expect(esquema.safeParse({ ...base, anio: '2013' }).success).toBe(false);
    expect(esquema.safeParse({ ...base, capacidad: '8' }).success).toBe(false);
    expect(esquema.safeParse({ ...base, anio: 'dos mil' }).success).toBe(false);
    expect(esquema.safeParse({ ...base, marca_modelo: 'x'.repeat(61) }).success).toBe(false);
  });

  it('conductor: licencia futura, móvil chileno y nombre no vacío', () => {
    const esquema = esquemaConductor('2026-11-03');
    const base = { nombre: 'Ana', rut: '12345678-5', telefono: '+56900001234', licencia_clase: 'A2' as const, licencia_vence: '2026-11-04' };
    expect(esquema.safeParse(base).success).toBe(true);
    expect(esquema.safeParse({ ...base, licencia_vence: '2026-11-03' }).success).toBe(false);
    expect(esquema.safeParse({ ...base, licencia_vence: '' }).success).toBe(false);
    expect(esquema.safeParse({ ...base, telefono: '+56221234567' }).success).toBe(false);
    expect(esquema.safeParse({ ...base, nombre: '   ' }).success).toBe(false);
  });

  it('cuerpos de edición: solo lo que cambió', () => {
    const vehiculo = { patente: 'BCDF10', marca_modelo: 'Kia Rio', anio: 2020, capacidad: 4 };
    expect(cuerpoEditarVehiculo({ ...vehiculo, anio: 2021, marca_modelo: 'Kia Soluto' }, vehiculo)).toEqual({
      anio: 2021,
      marca_modelo: 'Kia Soluto',
    });
    const conductor = { nombre: 'Ana', rut: '12345678-5', telefono: '+56900001234', licencia_clase: 'A2' as const, licencia_vence: '2027-01-01' };
    expect(cuerpoEditarConductor({ ...conductor, licencia_clase: 'A3' }, conductor)).toEqual({ licencia_clase: 'A3' });
  });
});

describe('licencia', () => {
  it('avisa vencida o por vencer en 30 días', () => {
    expect(diasHasta('2026-11-13', '2026-11-03')).toBe(10);
    expect(avisoLicencia('2026-11-03', '2026-11-03')).toBe('Licencia vencida');
    expect(avisoLicencia('2026-11-04', '2026-11-03')).toBe('Vence mañana');
    expect(avisoLicencia('2026-12-03', '2026-11-03')).toBe('Vence en 30 días');
    expect(avisoLicencia('2026-12-04', '2026-11-03')).toBeNull();
  });
});
