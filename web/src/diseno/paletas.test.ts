/** CC-27 (DC-84): los tokens de las paletas salen de la única fuente y no cambian los colores de estado. */

import { describe, expect, it } from 'vitest';
import catalogo from '../../../backend/apps/cuentas/paletas.json';
import { generar, tokensDe } from '../../scripts/generar-paletas.mjs';
import paletas from './paletas.css?raw';
import generado from './paletas.generado.ts?raw';
import tokens from './tokens.css?raw';

const normalizar = (texto: string) => texto.replace(/\r\n/g, '\n');

function contraste(a: string, b: string) {
  const luminancia = (c: string) => {
    const [r, g, azul] = [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16) / 255).map((v) => (v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * r + 0.7152 * g + 0.0722 * azul;
  };
  const [claro, oscuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (oscuro + 0.05);
}

describe('paletas generadas', () => {
  it('paletas.css y paletas.generado.ts están al día con paletas.json (node scripts/generar-paletas.mjs)', () => {
    const { css, ts } = generar(catalogo, normalizar(tokens));
    expect(normalizar(paletas)).toBe(css);
    expect(normalizar(generado)).toBe(ts);
  });

  it('Tiffany son los tokens vigentes de CC-20', () => {
    const bloque = normalizar(paletas).split('/* Océano */')[0];
    for (const [token, valor] of [
      ['--color-primario-900', '#0b4f5c'],
      ['--color-primario-700', '#0c7f7d'],
      ['--color-tiffany', '#81d8d0'],
      ['--fondo', '#f2fbfa'],
      ['--borde-campo', '#5f8f8b'],
    ]) {
      expect(bloque).toContain(`${token}: ${valor};`);
    }
  });

  it('ninguna paleta toca los colores de estado', () => {
    expect(paletas).not.toMatch(/--(insignia|exito|peligro|error)[a-z-]*:/);
    // Los fondos de estado tienen valor propio: no dependen de la marca.
    expect(tokens).toMatch(/--insignia-info-fondo: #81d8d0;/);
    expect(tokens).toMatch(/--insignia-neutra-fondo: #ddf3f1;/);
  });

  // Los tokens derivados que se mezclan con blanco también deben leerse bien (texto de tokens.css: oscuro y suave).
  it.each(catalogo.paletas.filter((p) => p.clave !== catalogo.predeterminada))('$nombre: contraste de los tokens derivados', (paleta) => {
    const t: Record<string, string> = tokensDe(paleta);
    for (const [texto, fondo, minimo] of [
      ['#0f2a2e', t['--fondo'], 4.5],
      ['#0f2a2e', t['--color-tiffany'], 4.5],
      ['#4f6a6c', t['--fondo'], 4.5],
      ['#4f6a6c', t['--suave'], 4.5],
      [t['--color-primario-900'], t['--color-tiffany-50'], 4.5],
      [t['--borde-campo'], '#ffffff', 3],
      [t['--borde-campo'], t['--fondo'], 3],
    ] as const) {
      expect(contraste(texto, fondo), `${texto} sobre ${fondo}`).toBeGreaterThanOrEqual(minimo);
    }
  });
});
