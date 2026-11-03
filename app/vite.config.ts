/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Cobertura mínima de la lógica de la app (DoD: ≥ 70 % en lo tocado). Las pantallas y los envoltorios de
// plugins nativos se prueban en el emulador y en el teléfono (docs/guia-prueba-app-android.md).
const MINIMO = { lines: 70, functions: 70, branches: 70, statements: 70 };

export default defineConfig({
  plugins: [react()],
  // Desarrollo en el navegador (`npm run dev` con VITE_API_URL vacío): la API queda en el mismo origen.
  server: { proxy: { '/api': 'http://127.0.0.1:8000', '/ws': { target: 'ws://127.0.0.1:8000', ws: true } } },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    coverage: {
      enabled: true,
      provider: 'v8',
      include: ['src/api.ts', 'src/perfil.ts', 'src/navegacion.ts', 'src/conductor/canal.ts', 'src/sesion/sesion.ts', 'src/gps/envio.ts', 'src/gps/turno.ts', 'src/gps/muestreo.ts'],
      thresholds: MINIMO,
    },
  },
});
