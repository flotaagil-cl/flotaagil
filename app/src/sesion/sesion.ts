/**
 * Sesión de la app del conductor (canal «app» del backend).
 *
 * - El refresh se guarda cifrado en el teléfono (almacenamiento respaldado por Android Keystore, ver almacen.ts);
 *   el access vive solo en memoria y se pide de nuevo al abrir la app.
 * - Renovar es una sola operación compartida: si varias peticiones reciben 401 a la vez (p. ej. el envío del GPS
 *   y una pantalla), se hace un solo refresh y todas esperan su resultado. El backend rota el refresh en cada
 *   renovación, así que dos renovaciones en paralelo cerrarían la sesión.
 * - Si la renovación falla por red (sin señal, app en segundo plano), el refresh se conserva y se reintenta
 *   después; solo un 401 del backend cierra la sesión.
 * - Con una contraseña temporal pendiente (DC-14) la sesión queda en «cambio_pendiente» hasta cambiarla.
 */

import type { AlmacenRefresh } from './almacen';

export interface Usuario {
  id: number;
  nombre: string;
  email: string;
  rol: string;
  debe_cambiar_password: boolean;
  empresa: { id: number; razon_social: string; slug: string };
}

export type EstadoSesion =
  | { fase: 'cargando' }
  | { fase: 'sin_sesion'; motivo?: string }
  | { fase: 'cambio_pendiente'; usuario: Usuario }
  | { fase: 'activa'; usuario: Usuario };

export type Http = (url: string, init: RequestInit) => Promise<Response>;

/** No hubo respuesta del backend (red). */
export class SinRed extends Error {
  constructor() {
    super('Sin conexión con el servidor.');
  }
}

/** La sesión terminó (refresh rechazado o cerrada): hay que volver a ingresar. */
export class SinSesion extends Error {
  constructor() {
    super('La sesión terminó.');
  }
}

/** Error de la API con su estado y cuerpo (`detail`, `code` o errores por campo). */
export class ErrorApi extends Error {
  constructor(
    readonly estado: number,
    readonly cuerpo: Record<string, unknown> | null,
  ) {
    super(typeof cuerpo?.detail === 'string' ? cuerpo.detail : `HTTP ${estado}`);
  }

  get codigo(): string | null {
    return typeof this.cuerpo?.code === 'string' ? this.cuerpo.code : null;
  }
}

const JSON_CT = { 'Content-Type': 'application/json' };

async function leer(respuesta: Response): Promise<Record<string, unknown> | null> {
  try {
    const datos: unknown = await respuesta.json();
    return datos && typeof datos === 'object' ? (datos as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

export class SesionApp {
  private accessActual: string | null = null;
  private renovacion: Promise<string | null> | null = null;
  private estadoActual: EstadoSesion = { fase: 'cargando' };
  private oyentes = new Set<(estado: EstadoSesion) => void>();

  constructor(
    private readonly http: Http,
    private readonly almacen: AlmacenRefresh,
    readonly base: string,
  ) {}

  get estado(): EstadoSesion {
    return this.estadoActual;
  }

  get access(): string | null {
    return this.accessActual;
  }

  suscribir(oyente: (estado: EstadoSesion) => void): () => void {
    this.oyentes.add(oyente);
    return () => this.oyentes.delete(oyente);
  }

  private cambiar(estado: EstadoSesion) {
    this.estadoActual = estado;
    this.oyentes.forEach((oyente) => oyente(estado));
  }

  private async post(ruta: string, cuerpo: unknown, access?: string): Promise<Response> {
    try {
      return await this.http(`${this.base}${ruta}`, {
        method: 'POST',
        headers: access ? { ...JSON_CT, Authorization: `Bearer ${access}` } : JSON_CT,
        body: JSON.stringify(cuerpo),
      });
    } catch {
      throw new SinRed();
    }
  }

  /** Al abrir la app: con un refresh guardado, renueva y consulta el usuario. */
  async iniciar(): Promise<void> {
    const refresh = await this.almacen.leer();
    if (!refresh) return this.cambiar({ fase: 'sin_sesion' });
    try {
      const access = await this.renovar();
      if (!access) return; // renovar() ya dejó la sesión cerrada
      await this.cargarUsuario();
    } catch (error) {
      // Sin red al abrir: se conserva el refresh y se ofrece reintentar desde el login.
      if (error instanceof SinRed) this.cambiar({ fase: 'sin_sesion', motivo: 'sin_conexion' });
      else throw error;
    }
  }

  private async cargarUsuario(): Promise<void> {
    let respuesta: Response;
    try {
      respuesta = await this.http(`${this.base}/api/auth/yo/`, {
        method: 'GET',
        headers: { Authorization: `Bearer ${this.accessActual}` },
      });
    } catch {
      throw new SinRed();
    }
    if (!respuesta.ok) {
      await this.terminar('sesion_terminada');
      return;
    }
    this.ponerUsuario((await respuesta.json()) as Usuario);
  }

  private ponerUsuario(usuario: Usuario) {
    this.cambiar(usuario.debe_cambiar_password ? { fase: 'cambio_pendiente', usuario } : { fase: 'activa', usuario });
  }

  async login(email: string, password: string): Promise<void> {
    const respuesta = await this.post('/api/auth/app/token/', { email, password });
    const cuerpo = await leer(respuesta);
    if (!respuesta.ok) throw new ErrorApi(respuesta.status, cuerpo);
    const datos = cuerpo as { access: string; refresh: string; usuario: Usuario };
    await this.almacen.guardar(datos.refresh);
    this.accessActual = datos.access;
    this.ponerUsuario(datos.usuario);
  }

  /**
   * Renueva el access con el refresh guardado. Devuelve el access nuevo, o null si la sesión terminó.
   * Lanza SinRed si no hubo respuesta (el refresh se conserva para reintentar).
   */
  renovar(): Promise<string | null> {
    this.renovacion ??= this.hacerRenovacion().finally(() => {
      this.renovacion = null;
    });
    return this.renovacion;
  }

  private async hacerRenovacion(): Promise<string | null> {
    const refresh = await this.almacen.leer();
    if (!refresh) {
      await this.terminar('sesion_terminada');
      return null;
    }
    const respuesta = await this.post('/api/auth/app/refresh/', { refresh });
    if (respuesta.status === 401) {
      await this.terminar('sesion_terminada');
      return null;
    }
    if (!respuesta.ok) throw new SinRed(); // 5xx: se trata como falta de red y se reintenta después
    const datos = (await respuesta.json()) as { access: string; refresh: string };
    // Primero se guarda el refresh nuevo: el anterior ya quedó en la lista negra del backend.
    await this.almacen.guardar(datos.refresh);
    this.accessActual = datos.access;
    return datos.access;
  }

  /** Una respuesta 403 `cambio_password_requerido` deja la sesión pidiendo el cambio. */
  marcarCambioPendiente() {
    const estado = this.estadoActual;
    if (estado.fase === 'activa') {
      this.cambiar({ fase: 'cambio_pendiente', usuario: { ...estado.usuario, debe_cambiar_password: true } });
    }
  }

  /** Cambia la contraseña (la temporal u otra). El backend cierra las demás sesiones y entrega tokens nuevos. */
  async cambiarPassword(actual: string, nueva: string): Promise<void> {
    const estado = this.estadoActual;
    if (estado.fase !== 'cambio_pendiente' && estado.fase !== 'activa') throw new SinSesion();
    const intentar = (access: string | null) =>
      this.post('/api/auth/password/', { password_actual: actual, password_nueva: nueva }, access ?? undefined);
    let respuesta = await intentar(this.accessActual);
    if (respuesta.status === 401) {
      const access = await this.renovar();
      if (!access) throw new SinSesion();
      respuesta = await intentar(access);
    }
    const cuerpo = await leer(respuesta);
    if (!respuesta.ok) throw new ErrorApi(respuesta.status, cuerpo);
    const datos = cuerpo as { access: string; refresh: string };
    await this.almacen.guardar(datos.refresh);
    this.accessActual = datos.access;
    this.cambiar({ fase: 'activa', usuario: { ...estado.usuario, debe_cambiar_password: false } });
  }

  /** Cierra la sesión en el backend (si hay red) y en el teléfono (siempre). */
  async logout(): Promise<void> {
    const refresh = await this.almacen.leer();
    if (refresh) {
      try {
        await this.post('/api/auth/app/logout/', { refresh });
      } catch {
        // Sin red: el refresh se borra igual del teléfono; en el backend vence solo (JWT_REFRESH_HORAS).
      }
    }
    await this.terminar();
  }

  private async terminar(motivo?: string) {
    this.accessActual = null;
    await this.almacen.borrar();
    this.cambiar({ fase: 'sin_sesion', ...(motivo && { motivo }) });
  }
}
