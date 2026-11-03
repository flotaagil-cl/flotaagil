/**
 * Dónde se guarda el refresh de la app.
 *
 * En Android se usa @aparajita/capacitor-secure-storage (7.x, para Capacitor 7): cifra cada valor con una clave
 * AES que vive en el Android Keystore y no se puede extraer del teléfono. El access no se guarda nunca.
 * En el navegador (desarrollo con `npm run dev`) el plugin usa localStorage: solo para probar la interfaz.
 */

import { SecureStorage } from '@aparajita/capacitor-secure-storage';

export interface AlmacenRefresh {
  leer(): Promise<string | null>;
  guardar(refresh: string): Promise<void>;
  borrar(): Promise<void>;
}

const CLAVE = 'refresh';

export function almacenSeguro(): AlmacenRefresh {
  void SecureStorage.setKeyPrefix('flotaagil_');
  return {
    async leer() {
      try {
        const valor = await SecureStorage.get(CLAVE);
        return typeof valor === 'string' ? valor : null;
      } catch {
        // Dato ilegible (p. ej. la clave del Keystore se invalidó): se trata como sin sesión.
        return null;
      }
    },
    async guardar(refresh) {
      await SecureStorage.set(CLAVE, refresh);
    },
    async borrar() {
      try {
        await SecureStorage.remove(CLAVE);
      } catch {
        // Ya no estaba.
      }
    },
  };
}

/** Para pruebas: guarda en memoria. */
export function almacenEnMemoria(inicial: string | null = null): AlmacenRefresh & { valor: string | null } {
  return {
    valor: inicial,
    async leer() {
      return this.valor;
    },
    async guardar(refresh) {
      this.valor = refresh;
    },
    async borrar() {
      this.valor = null;
    },
  };
}
