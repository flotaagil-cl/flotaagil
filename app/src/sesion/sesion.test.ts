import { describe, expect, it } from 'vitest';
import { Api } from '../api';
import { BackendFalso } from '../pruebas/backendFalso';
import { almacenEnMemoria } from './almacen';
import { ErrorApi, SesionApp, SinSesion } from './sesion';

function armar(refresh: string | null = null) {
  const backend = new BackendFalso();
  const almacen = almacenEnMemoria(refresh);
  const sesion = new SesionApp(backend.http, almacen, 'http://api.prueba');
  return { backend, almacen, sesion, api: new Api(backend.http, sesion) };
}

describe('login y almacenamiento', () => {
  it('guarda solo el refresh; el access queda en memoria', async () => {
    const { sesion, almacen } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    expect(sesion.estado.fase).toBe('activa');
    expect(almacen.valor).toMatch(/^R/);
    expect(sesion.access).toMatch(/^A/);
  });

  it('credenciales inválidas', async () => {
    const { sesion, almacen } = armar();
    await expect(sesion.login('x@x.example', 'mala')).rejects.toMatchObject({ estado: 401, codigo: 'credenciales_invalidas' });
    expect(almacen.valor).toBeNull();
  });

  it('al abrir con un refresh guardado renueva y consulta el usuario', async () => {
    const { backend, sesion, almacen } = armar();
    almacen.valor = backend.emitir().refresh;
    await sesion.iniciar();
    expect(sesion.estado).toMatchObject({ fase: 'activa', usuario: { nombre: 'Carla Conductora' } });
    expect(backend.llamadas).toEqual(['POST /api/auth/app/refresh/', 'GET /api/auth/yo/']);
  });

  it('sin refresh guardado, pide ingresar', async () => {
    const { sesion, backend } = armar();
    await sesion.iniciar();
    expect(sesion.estado).toEqual({ fase: 'sin_sesion' });
    expect(backend.llamadas).toEqual([]);
  });

  it('sin red al abrir conserva el refresh', async () => {
    const { backend, sesion, almacen } = armar();
    almacen.valor = backend.emitir().refresh;
    backend.sinRed = true;
    await sesion.iniciar();
    expect(sesion.estado).toEqual({ fase: 'sin_sesion', motivo: 'sin_conexion' });
    expect(almacen.valor).not.toBeNull();
  });

  it('un refresh rechazado cierra la sesión y lo borra', async () => {
    const { sesion, almacen } = armar('R-viejo');
    await sesion.iniciar();
    expect(sesion.estado).toEqual({ fase: 'sin_sesion', motivo: 'sesion_terminada' });
    expect(almacen.valor).toBeNull();
  });
});

describe('renovación', () => {
  it('varios 401 a la vez hacen un solo refresh (el backend rota el refresh)', async () => {
    const { backend, sesion, api } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    backend.vencerAccess();
    const lote = (n: number) => ({ posiciones: [{ lat: -33.4, lon: -70.6, precision_m: 5, registrada_en: `2026-11-03T12:00:0${n}Z` }] });
    await Promise.all([1, 2, 3].map((n) => api.pedir('POST', '/api/app/posiciones/', lote(n))));
    expect(backend.llamadas.filter((l) => l === 'POST /api/auth/app/refresh/')).toHaveLength(1);
    expect(backend.posiciones.size).toBe(3);
    expect(sesion.estado.fase).toBe('activa');
  });

  it('si el refresh falla por red, el refresh se conserva y la siguiente vez renueva', async () => {
    const { backend, sesion, api, almacen } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    const guardado = almacen.valor;
    backend.vencerAccess();
    backend.cortes.set('POST /api/auth/app/refresh/', 1);
    await expect(api.pedir('GET', '/api/auth/yo/')).rejects.toThrow('Sin conexión');
    expect(almacen.valor).toBe(guardado);
    expect(sesion.estado.fase).toBe('activa');
    await expect(api.pedir('GET', '/api/auth/yo/')).resolves.toMatchObject({ nombre: 'Carla Conductora' });
  });

  it('un refresh rechazado durante una petición termina la sesión', async () => {
    const { backend, sesion, api } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    backend.vencerAccess();
    await sesion.logout(); // el refresh queda en la lista negra
    await expect(api.pedir('GET', '/api/auth/yo/')).rejects.toBeInstanceOf(SinSesion);
  });
});

describe('contraseña temporal (DC-14)', () => {
  it('login con la temporal: pide el cambio; al cambiar queda activa con tokens nuevos', async () => {
    const { backend, sesion, almacen, api } = armar();
    backend.debeCambiar = true;
    await sesion.login('conductor1@andes.example', 'clave');
    expect(sesion.estado.fase).toBe('cambio_pendiente');
    const anterior = almacen.valor;
    await sesion.cambiarPassword('clave', 'otra-clave-segura');
    expect(sesion.estado.fase).toBe('activa');
    expect(almacen.valor).not.toBe(anterior);
    await expect(api.pedir('GET', '/api/auth/yo/')).resolves.toMatchObject({ debe_cambiar_password: false });
  });

  it('un 403 cambio_password_requerido en cualquier petición pasa a pedir el cambio', async () => {
    const { backend, sesion, api } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    backend.debeCambiar = true;
    await expect(api.pedir('POST', '/api/app/posiciones/', { posiciones: [] })).rejects.toBeInstanceOf(ErrorApi);
    expect(sesion.estado.fase).toBe('cambio_pendiente');
  });

  it('contraseña actual incorrecta: error por campo', async () => {
    const { backend, sesion } = armar();
    backend.debeCambiar = true;
    await sesion.login('conductor1@andes.example', 'clave');
    await expect(sesion.cambiarPassword('mala', 'otra-clave-segura')).rejects.toMatchObject({
      estado: 400,
      cuerpo: { password_actual: ['La contraseña actual no es correcta.'] },
    });
  });

  it('con el access vencido, el cambio renueva y se completa', async () => {
    const { backend, sesion } = armar();
    backend.debeCambiar = true;
    await sesion.login('conductor1@andes.example', 'clave');
    backend.vencerAccess();
    await sesion.cambiarPassword('clave', 'otra-clave-segura');
    expect(sesion.estado.fase).toBe('activa');
  });
});

describe('logout (PR-02)', () => {
  it('invalida el refresh en el backend y lo borra del teléfono', async () => {
    const { backend, sesion, almacen } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    await sesion.logout();
    expect(backend.llamadas).toContain('POST /api/auth/app/logout/');
    expect(backend.refreshActivos).toBe(0);
    expect(almacen.valor).toBeNull();
    expect(sesion.access).toBeNull();
    expect(sesion.estado).toEqual({ fase: 'sin_sesion' });
  });

  it('sin red borra igual del teléfono', async () => {
    const { backend, sesion, almacen } = armar();
    await sesion.login('conductor1@andes.example', 'clave');
    backend.sinRed = true;
    await sesion.logout();
    expect(almacen.valor).toBeNull();
  });
});
