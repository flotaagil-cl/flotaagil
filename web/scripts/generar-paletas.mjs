// CC-27 (DC-84): genera desde la única fuente del catálogo (backend/apps/cuentas/paletas.json)
//   - src/diseno/paletas.css: los tokens de marca de cada paleta, para el atributo data-paleta;
//   - src/diseno/paletas.generado.ts: claves y nombres (sin colores).
// Uso: node scripts/generar-paletas.mjs   (la prueba paletas.test.ts exige que estén al día)
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BLANCO = '#ffffff';

/** `peso` del primer color sobre el segundo, en sRGB. */
export function mezclar(color, fondo, peso) {
  const canal = (c, i) => parseInt(c.slice(i, i + 2), 16);
  return `#${[1, 3, 5]
    .map((i) => Math.round(canal(color, i) * peso + canal(fondo, i) * (1 - peso)).toString(16).padStart(2, '0'))
    .join('')}`;
}

/**
 * Tokens que una paleta reemplaza. Los de estado (éxito, error, advertencia y estados de reserva) no están:
 * no cambian con la paleta.
 */
export function tokensDe({ oscuro, medio, claro }) {
  return {
    '--color-primario-900': oscuro,
    '--color-primario-700': medio,
    '--color-tiffany': mezclar(medio, BLANCO, 0.35),
    '--color-tiffany-50': claro,
    '--color-hero-fin': medio,
    '--fondo': mezclar(claro, BLANCO, 0.5),
    '--borde': mezclar(medio, BLANCO, 0.18),
    '--borde-campo': mezclar(medio, BLANCO, 0.85),
    '--suave': mezclar(medio, BLANCO, 0.1),
    '--mapa': mezclar(medio, BLANCO, 0.12),
  };
}

/** Tiffany son los tokens vigentes de CC-20: se leen de tokens.css, no se recalculan. */
function tokensVigentes(css, claves) {
  return Object.fromEntries(
    claves.map((clave) => {
      const encontrado = css.match(new RegExp(`^\\s+${clave}:\\s*(#[0-9a-fA-F]{6});`, 'm'));
      if (!encontrado) throw new Error(`tokens.css no define ${clave}`);
      return [clave, encontrado[1].toLowerCase()];
    }),
  );
}

export function generar(catalogo, tokensCss) {
  const bloques = catalogo.paletas.map((paleta) => {
    const calculados = tokensDe(paleta);
    const tokens = paleta.clave === catalogo.predeterminada ? tokensVigentes(tokensCss, Object.keys(calculados)) : calculados;
    const selectores = ['.tema-portal', '.tema-flotaagil'].flatMap((tema) => [`${tema}[data-paleta='${paleta.clave}']`, `${tema} [data-paleta='${paleta.clave}']`]);
    return `/* ${paleta.nombre} */\n${selectores.join(',\n')} {\n${Object.entries(tokens)
      .map(([clave, valor]) => `  ${clave}: ${valor};`)
      .join('\n')}\n}`;
  });
  const aviso = 'Generado por scripts/generar-paletas.mjs desde backend/apps/cuentas/paletas.json. No editar a mano.';
  const css = `/* CC-27 (DC-84): paletas por empresa. ${aviso} */\n\n${bloques.join('\n\n')}\n`;
  const lista = catalogo.paletas.map((p) => `  { clave: '${p.clave}', nombre: '${p.nombre}' },`).join('\n');
  const ts = `// ${aviso}\nexport const PALETA_PREDETERMINADA = '${catalogo.predeterminada}';\n\nexport const PALETAS = [\n${lista}\n] as const;\n\nexport type ClavePaleta = (typeof PALETAS)[number]['clave'];\n`;
  return { css, ts };
}

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const leer = (ruta) => readFileSync(join(RAIZ, ruta), 'utf8');
  const { css, ts } = generar(JSON.parse(leer('../backend/apps/cuentas/paletas.json')), leer('src/diseno/tokens.css').replace(/\r\n/g, '\n'));
  writeFileSync(join(RAIZ, 'src/diseno/paletas.css'), css);
  writeFileSync(join(RAIZ, 'src/diseno/paletas.generado.ts'), ts);
  console.log('paletas.css y paletas.generado.ts actualizados');
}
