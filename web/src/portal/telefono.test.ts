import { describe, expect, it } from 'vitest';
import { errorTelefono, mostrarTelefono, normalizarTelefono, sugerenciaChile } from './telefono';

describe('teléfono del portal (turistas)', () => {
  it.each([
    ['987654321', '+56987654321'],
    ['9 8765 4321', '+56987654321'],
    ['9-8765-4321', '+56987654321'],
  ])('«%s» sin prefijo: sugiere %s (no lo cambia solo)', (valor, sugerido) => {
    expect(sugerenciaChile(valor)).toBe(sugerido);
    expect(errorTelefono(valor)).toBe('Incluye el código de país, por ejemplo +56 9… (Chile) o +51 9… (Perú).');
  });

  it.each(['+51987654321', '+56987654321', '812345678', '98765432', '9876543210', ''])('«%s»: sin sugerencia', (valor) => {
    expect(sugerenciaChile(valor)).toBeNull();
  });

  it.each(['+51 987 654 321', '+34 912 345 678', '+1 (415) 555-0100', '+56 9 8765 4321'])('«%s»: número internacional válido', (valor) => {
    expect(errorTelefono(valor)).toBeNull();
  });

  it('errores', () => {
    expect(errorTelefono('  ')).toBe('Ingresa tu número de WhatsApp.');
    expect(errorTelefono('+0123')).toBe('Número en formato internacional, p. ej. +56 9 1234 5678.');
    expect(errorTelefono('12345678')).toContain('Incluye el código de país');
  });

  it('normaliza como el backend y muestra los celulares chilenos agrupados', () => {
    expect(normalizarTelefono('+51 (987) 654-321')).toBe('+51987654321');
    expect(mostrarTelefono('+56987654321')).toBe('+56 9 8765 4321');
    expect(mostrarTelefono('+51987654321')).toBe('+51987654321');
  });
});
