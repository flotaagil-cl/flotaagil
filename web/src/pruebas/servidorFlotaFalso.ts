/**
 * /api/vehiculos/ y /api/conductores/ falsos, montados sobre el servidor de auth falso. Las demás rutas pasan
 * al manejador que ya estaba (el de reservas). Imita lo que la interfaz usa del backend: listados paginados de
 * a 25 con `q` y `activo`, registrar (400 si la patente existe), editar y desactivar (409 si un conductor lo
 * tiene declarado en turno), importar CSV (informe; todo o nada), editar el conductor y asociar o quitar
 * vehículos (409 si es el declarado en turno). `siguiente` programa la próxima respuesta de una ruta.
 */

import type { Conductor, ConductorCrear, ConductorEditar, Informe, Vehiculo, VehiculoCrear, VehiculoEditar } from '../flota/api';
import type { Respuesta, ServidorAuthFalso } from './servidorAuthFalso';

let siguienteId = 500;

export function vehiculoDePrueba(cambios: Partial<Vehiculo> = {}): Vehiculo {
  return {
    id: cambios.id ?? ++siguienteId,
    patente: 'BCDF10',
    marca_modelo: 'Toyota Yaris',
    anio: 2024,
    capacidad: 4,
    activo: true,
    conductores: [],
    ...cambios,
  };
}

export function conductorDePrueba(cambios: Partial<Conductor> = {}): Conductor {
  return {
    id: cambios.id ?? ++siguienteId,
    nombre: 'Pedro Soto',
    email: 'conductor1@andes.example',
    activo: true,
    rut: '15000100-5',
    telefono: '+56900001001',
    licencia_clase: 'A2',
    licencia_vence: '2027-12-31',
    licencia_vigente: true,
    estado: 'NO_DISPONIBLE',
    vehiculo_activo: null,
    consentimiento_gps_en: null,
    acceso: 'ACTIVA',
    password_temporal_vence: null,
    vehiculos: [],
    ...cambios,
  };
}

type Manejador = (peticion: Request, url: URL) => Promise<Respuesta>;

export class ServidorFlotaFalso {
  vehiculos: Vehiculo[] = [];
  conductores: Conductor[] = [];
  /** Cuerpos recibidos, por ruta. El CSV se registra como `{archivo: nombre, confirmar}`. */
  cuerpos: { ruta: string; cuerpo: unknown }[] = [];
  /** Lo que responde el próximo POST a importar; si no hay, un informe válido con una fila. */
  informes: Respuesta[] = [];
  private programadas = new Map<string, Respuesta[]>();
  private anterior: Manejador | null;

  constructor(readonly auth: ServidorAuthFalso) {
    this.anterior = auth.api;
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  siguiente(ruta: string, respuesta: Respuesta) {
    this.programadas.set(ruta, [...(this.programadas.get(ruta) ?? []), respuesta]);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    const ruta = `${peticion.method} ${url.pathname}`;
    const esFlota = /^\/api\/(vehiculos|conductores)\//.test(url.pathname);
    if (!esFlota) {
      return this.anterior ? this.anterior(peticion, url) : { estado: 404, cuerpo: { detail: 'No encontrado.' } };
    }
    if (ruta === 'POST /api/vehiculos/importar/' || ruta === 'POST /api/conductores/importar/') {
      const formulario = await peticion.formData();
      const archivo = formulario.get('archivo');
      this.cuerpos.push({
        ruta,
        cuerpo: { archivo: typeof archivo === 'string' ? archivo : archivo?.name, confirmar: formulario.get('confirmar') },
      });
      return this.informes.shift() ?? { estado: 200, cuerpo: informeDePrueba() };
    }
    // Algunas acciones (password, deshabilitar…) van sin cuerpo.
    const texto = peticion.method === 'GET' || peticion.method === 'DELETE' ? '' : await peticion.text();
    const cuerpo: unknown = texto ? JSON.parse(texto) : undefined;
    if (cuerpo !== undefined) this.cuerpos.push({ ruta, cuerpo });
    const programada = this.programadas.get(ruta)?.shift();
    if (programada) return programada;

    if (ruta === 'GET /api/vehiculos/') return paginar(this.filtrarVehiculos(url), url);
    if (ruta === 'POST /api/vehiculos/') return this.crearVehiculo(cuerpo as VehiculoCrear);
    if (ruta === 'GET /api/conductores/') return paginar(this.filtrarConductores(url), url);
    if (ruta === 'POST /api/conductores/') return this.crearConductor(cuerpo as ConductorCrear);

    const vehiculo = /^\/api\/vehiculos\/(\d+)\/$/.exec(url.pathname);
    if (vehiculo) {
      const encontrado = this.vehiculos.find((v) => v.id === Number(vehiculo[1]));
      if (!encontrado) return NO_ENCONTRADO;
      if (peticion.method === 'PATCH') return this.editarVehiculo(encontrado, cuerpo as VehiculoEditar);
      return { estado: 200, cuerpo: encontrado };
    }
    const conductor = /^\/api\/conductores\/(\d+)\/(?:vehiculos\/(?:(\d+)\/)?|(password|deshabilitar|habilitar|terminar-turno)\/)?$/.exec(url.pathname);
    const encontrado = conductor && this.conductores.find((c) => c.id === Number(conductor[1]));
    if (!conductor || !encontrado) return NO_ENCONTRADO;
    if (conductor[3]) return this.cuenta(encontrado, conductor[3]);
    if (url.pathname.includes('/vehiculos/')) {
      if (peticion.method === 'POST') return this.asociar(encontrado, (cuerpo as { vehiculo: number }).vehiculo);
      return this.quitar(encontrado, Number(conductor[2]));
    }
    if (peticion.method === 'PATCH') {
      Object.assign(encontrado, cuerpo as ConductorEditar);
      return { estado: 200, cuerpo: encontrado };
    }
    return { estado: 200, cuerpo: encontrado };
  }

  /** Contraseña temporal entregada por el último `password/` (para comprobar que se muestra y se olvida). */
  ultimaTemporal: string | null = null;

  private crearConductor(datos: ConductorCrear): Respuesta {
    if (this.conductores.some((c) => c.email === datos.email)) {
      return { estado: 400, cuerpo: { email: ['Este correo ya tiene una cuenta.'] } };
    }
    const conductor = conductorDePrueba({ ...datos, acceso: 'SIN_PASSWORD' });
    this.conductores.push(conductor);
    return { estado: 201, cuerpo: conductor };
  }

  private cuenta(conductor: Conductor, accion: string): Respuesta {
    if (accion === 'terminar-turno') {
      // HU-31 (DC-32)
      if (conductor.estado === 'EN_VIAJE') return { estado: 409, cuerpo: { detail: 'Está en un viaje.', code: 'en_viaje' } };
      if (conductor.estado === 'NO_DISPONIBLE') return { estado: 409, cuerpo: { detail: 'No tiene un turno abierto.', code: 'sin_turno' } };
      Object.assign(conductor, { estado: 'NO_DISPONIBLE', vehiculo_activo: null });
      return { estado: 200, cuerpo: conductor };
    }
    if (conductor.estado === 'EN_VIAJE' && accion !== 'habilitar') {
      return { estado: 409, cuerpo: { detail: 'El conductor está en viaje: no se puede hacer esto hasta que termine.', code: 'conductor_en_viaje' } };
    }
    if (accion === 'password') {
      this.ultimaTemporal = `Tmp${++siguienteId}abcdEFGH`;
      Object.assign(conductor, { acceso: 'TEMPORAL', password_temporal_vence: '2026-11-06T15:00:00Z' });
      return { estado: 201, cuerpo: { password_temporal: this.ultimaTemporal, vence_en: '2026-11-06T15:00:00Z' } };
    }
    const activo = accion === 'habilitar';
    Object.assign(conductor, { activo, ...(activo ? {} : { estado: 'NO_DISPONIBLE' }) });
    return { estado: 200, cuerpo: conductor };
  }

  private filtrarVehiculos(url: URL): Vehiculo[] {
    const q = url.searchParams.get('q')?.toUpperCase();
    const activo = url.searchParams.get('activo');
    return this.vehiculos.filter(
      (v) =>
        (!q || v.patente.includes(q) || v.marca_modelo.toUpperCase().includes(q)) &&
        (activo === null || String(v.activo) === activo),
    );
  }

  private filtrarConductores(url: URL): Conductor[] {
    const q = url.searchParams.get('q')?.toLowerCase();
    const estado = url.searchParams.get('estado');
    return this.conductores.filter(
      (c) => (!q || c.nombre.toLowerCase().includes(q)) && (!estado || c.estado === estado),
    );
  }

  private crearVehiculo(datos: VehiculoCrear): Respuesta {
    if (this.vehiculos.some((v) => v.patente === datos.patente)) {
      return { estado: 400, cuerpo: { patente: ['Esta patente ya está registrada.'] } };
    }
    const vehiculo = vehiculoDePrueba({ ...datos, capacidad: datos.capacidad ?? 4 });
    this.vehiculos.push(vehiculo);
    return { estado: 201, cuerpo: vehiculo };
  }

  private enTurno(vehiculoId: number): Conductor | undefined {
    return this.conductores.find((c) => c.vehiculo_activo?.id === vehiculoId && c.estado !== 'NO_DISPONIBLE');
  }

  private editarVehiculo(vehiculo: Vehiculo, cambios: VehiculoEditar): Respuesta {
    const ocupado = cambios.activo === false && this.enTurno(vehiculo.id);
    if (ocupado) {
      return {
        estado: 409,
        cuerpo: {
          detail: `El vehículo está declarado por ${ocupado.nombre}, que está en turno. Debe quedar No disponible antes de desactivarlo.`,
          code: 'flota_en_uso',
        },
      };
    }
    Object.assign(vehiculo, cambios);
    return { estado: 200, cuerpo: vehiculo };
  }

  private asociar(conductor: Conductor, id: number): Respuesta {
    const vehiculo = this.vehiculos.find((v) => v.id === id);
    if (!vehiculo) return { estado: 400, cuerpo: { vehiculo: ['Clave primaria inválida.'] } };
    if (!vehiculo.activo) return { estado: 400, cuerpo: { vehiculo: ['El vehículo está inactivo.'] } };
    // Object.assign: los campos son de solo lectura en el esquema, pero aquí el servidor los cambia.
    Object.assign(conductor, {
      vehiculos: [
        ...conductor.vehiculos,
        { id, patente: vehiculo.patente, marca_modelo: vehiculo.marca_modelo, activo: true, desde: '2026-11-03' },
      ],
    });
    Object.assign(vehiculo, { conductores: [...vehiculo.conductores, { id: conductor.id, nombre: conductor.nombre }] });
    return { estado: 201, cuerpo: conductor };
  }

  private quitar(conductor: Conductor, id: number): Respuesta {
    if (conductor.vehiculo_activo?.id === id && conductor.estado !== 'NO_DISPONIBLE') {
      return {
        estado: 409,
        cuerpo: {
          detail: 'Es el vehículo declarado del turno en curso. El conductor debe quedar No disponible antes de quitarlo.',
          code: 'flota_en_uso',
        },
      };
    }
    Object.assign(conductor, { vehiculos: conductor.vehiculos.filter((v) => v.id !== id) });
    return { estado: 200, cuerpo: conductor };
  }
}

const NO_ENCONTRADO: Respuesta = { estado: 404, cuerpo: { detail: 'No encontrado.', code: 'not_found' } };

function paginar<T>(lista: T[], url: URL): Respuesta {
  const pagina = Number(url.searchParams.get('page') ?? 1);
  const conPagina = (n: number) => {
    const otra = new URL(url);
    otra.searchParams.set('page', String(n));
    return otra.toString();
  };
  return {
    estado: 200,
    cuerpo: {
      count: lista.length,
      next: pagina * 25 < lista.length ? conPagina(pagina + 1) : null,
      previous: pagina > 1 ? conPagina(pagina - 1) : null,
      results: lista.slice((pagina - 1) * 25, pagina * 25),
    },
  };
}

export function informeDePrueba(cambios: Partial<Informe> = {}): Informe {
  return {
    filas: [{ linea: 2, datos: { patente: 'GHJK20', marca_modelo: 'Kia Rio', anio: '2024', capacidad: '4' }, errores: {} }],
    validas: 1,
    con_errores: 0,
    creados: 0,
    ...cambios,
  };
}
