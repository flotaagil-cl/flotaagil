// DC-58 (CC-20): la app usa los mismos tokens que el portal y el panel. No se duplican a mano: este script copia
// web/src/diseno/tokens.css en app/src/diseno/tokens.css con una cabecera, y `tokens.test.ts` falla si la copia
// quedó atrás. Uso: npm run tokens (en app/).
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
export const ORIGEN = join(RAIZ, 'web', 'src', 'diseno', 'tokens.css');
export const DESTINO = join(RAIZ, 'app', 'src', 'diseno', 'tokens.css');
export const CABECERA = '/* GENERADO por app/scripts/copiar-tokens.mjs desde web/src/diseno/tokens.css: no editar a mano. */\n';

export function contenidoGenerado() {
  return CABECERA + readFileSync(ORIGEN, 'utf8').replace(/\r\n/g, '\n');
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  writeFileSync(DESTINO, contenidoGenerado());
  console.log(`tokens copiados en ${DESTINO}`);
}
