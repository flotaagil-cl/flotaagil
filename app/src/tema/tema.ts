/**
 * CC-27 (HU-80): el tema de la empresa en la app del conductor (paleta y logo).
 *
 * Llega con la sesión: se lee al ingresar o al abrir la app y queda guardado en el celular, con el logo incluido,
 * para que cargue sin conexión. No cambia en vivo. No es un dato secreto, así que no usa el almacenamiento cifrado.
 */

export interface AparienciaEmpresa {
  paleta: string;
  logo: { app: string } | null;
}

export interface Tema {
  paleta: string;
  empresa: string;
  /** El logo como data URL, para verlo sin red. `null`: se usa el de FlotaÁgil. */
  logo: string | null;
  /** De dónde salió el logo guardado; cambia cuando la empresa sube otro. */
  ruta: string | null;
}

type Almacen = Pick<Storage, 'getItem' | 'setItem'>;
/** Devuelve la imagen como data URL, o `null` si no se pudo descargar. */
export type DescargarImagen = (url: string) => Promise<string | null>;

export const CLAVE_TEMA = 'flotaagil.tema';

export function leerTema(almacen: Almacen | null): Tema | null {
  try {
    const datos = JSON.parse(almacen?.getItem(CLAVE_TEMA) ?? 'null') as Tema | null;
    return datos && typeof datos.paleta === 'string' ? datos : null;
  } catch {
    return null;
  }
}

export class TemaApp {
  private actual: Tema | null;
  private oyentes = new Set<() => void>();

  constructor(
    private readonly almacen: Almacen | null,
    private readonly descargar: DescargarImagen,
    private readonly base: string,
  ) {
    this.actual = leerTema(almacen);
  }

  leer = (): Tema | null => this.actual;

  suscribir = (oyente: () => void): (() => void) => {
    this.oyentes.add(oyente);
    return () => this.oyentes.delete(oyente);
  };

  /** Pone la paleta en el documento. Se llama antes de pintar, con lo guardado. */
  aplicar(raiz: HTMLElement = document.body): void {
    if (this.actual) raiz.dataset.paleta = this.actual.paleta;
  }

  /** Con la apariencia recibida al ingresar o al abrir. Un servidor sin este dato no cambia nada. */
  async actualizar(apariencia: AparienciaEmpresa | null | undefined, empresa: string): Promise<void> {
    if (!apariencia) return;
    const ruta = apariencia.logo?.app ?? null;
    const conocido = ruta !== null && this.actual?.ruta === ruta ? this.actual.logo : null;
    this.poner({ paleta: apariencia.paleta, empresa, logo: conocido, ruta: conocido ? ruta : null });
    if (!ruta || conocido) return;
    const logo = await this.descargar(`${this.base}${ruta}`);
    // Si no se pudo descargar queda el de FlotaÁgil y se reintenta la próxima vez que se abra.
    if (logo) this.poner({ paleta: apariencia.paleta, empresa, logo, ruta });
  }

  private poner(tema: Tema) {
    this.actual = tema;
    try {
      this.almacen?.setItem(CLAVE_TEMA, JSON.stringify(tema));
    } catch {
      // Sin espacio o sin almacenamiento: el tema vale solo mientras la app esté abierta.
    }
    this.aplicar();
    this.oyentes.forEach((oyente) => oyente());
  }
}
