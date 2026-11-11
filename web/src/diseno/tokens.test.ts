import { describe, expect, it } from 'vitest';
import tokens from './tokens.css?raw';

/** Valores de los tokens, resolviendo los var() que apuntan a otros tokens. */
function leerTokens(css: string): Record<string, string> {
  const crudos = Object.fromEntries([...css.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map(([, nombre, valor]) => [nombre, valor.trim()]));
  const resolver = (valor: string): string => valor.replace(/var\((--[\w-]+)\)/g, (_, nombre: string) => resolver(crudos[nombre] ?? ''));
  return Object.fromEntries(Object.entries(crudos).map(([nombre, valor]) => [nombre, resolver(valor)]));
}

function luminancia(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255).map((c) => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contraste(a: string, b: string): number {
  const [claro, oscuro] = [luminancia(a), luminancia(b)].sort((x, y) => y - x);
  return (claro + 0.05) / (oscuro + 0.05);
}

const t = leerTokens(tokens);

describe('HU-37 · tokens del portal', () => {
  it('tienen los valores del diseño', () => {
    expect(t['--color-primario-900']).toBe('#0b4f5c');
    expect(t['--color-primario-700']).toBe('#0c7f7d');
    expect(t['--color-tiffany']).toBe('#81d8d0');
    expect(t['--fondo']).toBe('#f2fbfa');
    expect(t['--texto']).toBe('#0f2a2e');
    expect(t['--grad-boton']).toBe('linear-gradient(90deg, #0b4f5c, #0c7f7d)');
  });

  // Texto normal: 4,5:1 (WCAG 1.4.3). Bordes de campos y foco: 3:1 (WCAG 1.4.11).
  it.each([
    ['--texto', '--fondo', 4.5],
    ['--texto', '--superficie', 4.5],
    ['--texto', '--color-tiffany', 4.5],
    ['--texto-suave', '--fondo', 4.5],
    ['--texto-suave', '--superficie', 4.5],
    ['--texto-suave', '--suave', 4.5],
    ['--sobre-oscuro', '--color-primario-900', 4.5],
    ['--sobre-oscuro', '--color-primario-700', 4.5],
    ['--sobre-oscuro', '--peligro', 4.5],
    ['--color-primario-700', '--superficie', 4.5],
    ['--peligro', '--superficie', 4.5],
    ['--exito', '--superficie', 4.5],
    ['--insignia-info-texto', '--insignia-info-fondo', 4.5],
    ['--insignia-ok-texto', '--insignia-ok-fondo', 4.5],
    ['--insignia-revision-texto', '--insignia-revision-fondo', 4.5],
    ['--insignia-peligro-texto', '--insignia-peligro-fondo', 4.5],
    ['--insignia-neutra-texto', '--insignia-neutra-fondo', 4.5],
    ['--borde-campo', '--superficie', 3],
    ['--borde-campo', '--fondo', 3],
    ['--foco', '--fondo', 3],
    ['--foco', '--superficie', 3],
  ])('%s sobre %s ≥ %s:1', (texto, fondo, minimo) => {
    expect(contraste(t[texto], t[fondo])).toBeGreaterThanOrEqual(minimo);
  });
});

describe('HU-37 · colores solo como tokens', () => {
  const fuentes = import.meta.glob<string>(['./**/*.{ts,tsx,css}', '!./**/*.test.{ts,tsx}', '!./tokens.css'], {
    query: '?raw',
    import: 'default',
    eager: true,
  });

  it('revisa los componentes', () => {
    expect(Object.keys(fuentes).length).toBeGreaterThan(10);
  });

  it.each(Object.entries(fuentes))('%s no tiene colores sueltos', (_archivo, codigo) => {
    expect(codigo).not.toMatch(/#[0-9a-f]{3,8}\b|\brgba?\(|\bhsla?\(/i);
  });
});
