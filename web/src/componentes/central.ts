/**
 * HU-49 (DC-80): contacto de la central en las pantallas de error del portal. Con el servidor caído no se
 * pueden pedir los números, así que se guardan cada vez que el portal carga la empresa y se leen de ahí.
 */

import type { Almacen } from '../entorno';

export interface NumerosCentral {
  telefono: string | null;
  whatsapp: string | null;
}

const PREFIJO = 'flotaagil.central.';
const ULTIMA = 'flotaagil.central';

/** Rutas del portal y de las cuentas web (pasajero y convenio): ahí el error ofrece llamar a la central. */
const RUTAS_PORTAL = /^\/(solicitar|pedir|mis-viajes|soporte|mi-perfil|mi-convenio)(\/|$)/;

export function esRutaDelPortal(ruta: string): boolean {
  return RUTAS_PORTAL.test(ruta);
}

export function slugDeRuta(ruta: string): string | null {
  return /^\/solicitar\/([^/]+)/.exec(ruta)?.[1] ?? null;
}

export function hayNumeros(central: NumerosCentral | null | undefined): central is NumerosCentral {
  return Boolean(central?.telefono || central?.whatsapp);
}

/** El WhatsApp vacío usa el teléfono de la central, que es un celular (el backend ya lo resuelve igual). */
export function conWhatsapp(central: NumerosCentral): NumerosCentral {
  return { telefono: central.telefono, whatsapp: central.whatsapp || central.telefono };
}

export function enlaceWhatsapp(numero: string): string {
  return `https://wa.me/${numero.replace(/\D/g, '')}`;
}

export function guardarCentral(almacen: Almacen | null, slug: string, central: NumerosCentral | null | undefined): void {
  if (!almacen || !slug) return;
  try {
    if (hayNumeros(central)) {
      const valor = JSON.stringify(conWhatsapp(central));
      almacen.setItem(PREFIJO + slug, valor);
      almacen.setItem(ULTIMA, valor);
    } else {
      almacen.removeItem(PREFIJO + slug);
    }
  } catch {
    // Sin almacenamiento: el error se muestra sin los botones.
  }
}

/** Los números guardados de esa empresa; sin slug (cuentas web), los de la última empresa cargada. */
export function leerCentral(almacen: Almacen | null, slug?: string | null): NumerosCentral | null {
  if (!almacen) return null;
  try {
    const texto = almacen.getItem(slug ? PREFIJO + slug : ULTIMA);
    if (!texto) return null;
    const valor = JSON.parse(texto) as Partial<NumerosCentral>;
    const central = { telefono: valor.telefono ?? null, whatsapp: valor.whatsapp ?? null };
    return hayNumeros(central) ? central : null;
  } catch {
    return null;
  }
}
