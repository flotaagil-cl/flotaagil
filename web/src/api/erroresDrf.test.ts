import { describe, expect, it } from 'vitest';
import { erroresDelBackend } from './erroresDrf';

describe('erroresDelBackend', () => {
  it('el `code` que acompaña a `detail` no se muestra (manejador de errores con code en toda la API)', () => {
    expect(erroresDelBackend({ detail: 'Conflicto.', code: 'conflicto_estado' }, {}, [])).toEqual({
      campos: {},
      generales: ['Conflicto.'],
    });
  });

  it('un campo llamado code dentro de un objeto sí se trata como campo', () => {
    expect(erroresDelBackend({ vuelo: { code: ['Inválido.'] } }, { 'vuelo.code': 'vuelo' }, ['vuelo'])).toEqual({
      campos: { vuelo: 'Inválido.' },
      generales: [],
    });
  });
});
