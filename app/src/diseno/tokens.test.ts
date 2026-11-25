/** DC-58 (CC-20, HU-59): la copia de los tokens en la app es exactamente la del web. */

import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
// @ts-expect-error: módulo de script en JavaScript, sin tipos.
import { contenidoGenerado, DESTINO, DESTINO_PALETAS, paletasGeneradas } from '../../scripts/copiar-tokens.mjs';

describe('tokens del sistema visual', () => {
  it('la copia de la app coincide con web/src/diseno/tokens.css (si falla: npm run tokens)', () => {
    expect(readFileSync(DESTINO, 'utf8').replace(/\r\n/g, '\n')).toBe(contenidoGenerado());
  });

  it('CC-27: las paletas de la app son las mismas del web (si falla: npm run tokens)', () => {
    expect(readFileSync(DESTINO_PALETAS, 'utf8').replace(/\r\n/g, '\n')).toBe(paletasGeneradas());
  });

  it('define el tema común de la app', () => {
    expect(contenidoGenerado()).toContain('.tema-flotaagil {');
  });
});
