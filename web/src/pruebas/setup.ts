import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';

// Las pantallas llegan con lazy (raíz de sesión → RutaAutenticada → Layout → pantalla): la primera carga de
// cada cadena transforma esos módulos, y con toda la suite y la cobertura corriendo en paralelo puede pasar
// del segundo que espera Testing Library por defecto.
configure({ asyncUtilTimeout: 5000 });

// jsdom trae un WebSocket real: ninguna pantalla debe abrir una conexión de verdad en las pruebas. Las que
// prueban el canal en vivo lo reemplazan por su propio doble.
class WebSocketInerte {
  onopen = null;
  onmessage = null;
  onclose = null;
  close() {}
}

beforeEach(() => {
  vi.stubGlobal('WebSocket', WebSocketInerte);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});
