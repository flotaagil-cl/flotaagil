// DC-58 (CC-20): la app usa los mismos tokens que el portal y el panel. No se duplican a mano: este script copia
// web/src/diseno/tokens.css en app/src/diseno/tokens.css con una cabecera, y `tokens.test.ts` falla si la copia
// quedó atrás. CC-27: copia igual las paletas por empresa (paletas.css). Uso: npm run tokens (en app/).
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const ORIGEN = join(RAIZ, 'web', 'src', 'diseno', 'tokens.css');
export const DESTINO = join(RAIZ, 'app', 'src', 'diseno', 'tokens.css');
export const ORIGEN_PALETAS = join(RAIZ, 'web', 'src', 'diseno', 'paletas.css');
export const DESTINO_PALETAS = join(RAIZ, 'app', 'src', 'diseno', 'paletas.css');
const cabecera = (archivo) => `/* GENERADO por app/scripts/copiar-tokens.mjs desde web/src/diseno/${archivo}: no editar a mano. */\n`;
export const CABECERA = cabecera('tokens.css');

const copia = (origen, encabezado) => encabezado + readFileSync(origen, 'utf8').replace(/\r\n/g, '\n');
export const contenidoGenerado = () => copia(ORIGEN, CABECERA);
export const paletasGeneradas = () => copia(ORIGEN_PALETAS, cabecera('paletas.css'));

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeFileSync(DESTINO, contenidoGenerado());
  writeFileSync(DESTINO_PALETAS, paletasGeneradas());
  console.log(`tokens y paletas copiados en ${dirname(DESTINO)}`);
}
