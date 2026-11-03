/**
 * Envío del GPS durante el turno. Lo central: el envío no se corta cuando vence el access (cada 15 min), tampoco
 * si la renovación falla por red con la app en segundo plano; las posiciones esperan en la cola y llegan sin
 * duplicarse.
 */

import { describe, expect, it } from 'vitest';
import { Api } from '../api';
import { BackendFalso } from '../pruebas/backendFalso';
import { almacenEnMemoria } from '../sesion/almacen';
import { SesionApp } from '../sesion/sesion';
import { ColaPosiciones, MAX_PENDIENTES, type PosicionApp } from './envio';
import { Rastreador, type Plugin } from './turno';
import type { Location } from './rastreo';

async function armar() {
  const backend = new BackendFalso();
  const sesion = new SesionApp(backend.http, almacenEnMemoria(), 'http://api.prueba');
  await sesion.login('conductor1@andes.example', 'clave');
  let reloj = Date.parse('2026-11-03T12:00:00Z');
  const ahora = () => reloj;
  const avanzar = (ms: number) => {
    reloj += ms;
  };
  const cola = new ColaPosiciones(new Api(backend.http, sesion), ahora);
  return { backend, sesion, cola, ahora, avanzar };
}

const posicion = (segundo: number): PosicionApp => ({
  lat: -33.4,
  lon: -70.6,
  precision_m: 6,
  registrada_en: new Date(Date.parse('2026-11-03T12:00:00Z') + segundo * 1000).toISOString(),
});

describe('cola de posiciones', () => {
  it('un viaje de 1 h con el access venciendo cada 15 min: llegan todas, sin cortes', async () => {
    const { backend, cola, avanzar } = await armar();
    for (let s = 0; s < 3600; s += 10) {
      if (s > 0 && s % 900 === 0) backend.vencerAccess();
      avanzar(10_000);
      await cola.agregar(posicion(s));
    }
    expect(backend.posiciones.size).toBe(360);
    expect(cola.estado).toMatchObject({ pendientes: 0, error: null });
    expect(backend.llamadas.filter((l) => l === 'POST /api/auth/app/refresh/')).toHaveLength(3);
  });

  it('renovación sin red en segundo plano: las posiciones esperan y llegan al volver la señal, sin duplicar', async () => {
    const { backend, cola, avanzar, sesion } = await armar();
    await cola.agregar(posicion(0));
    backend.vencerAccess();
    backend.sinRed = true;
    for (let s = 10; s <= 60; s += 10) {
      avanzar(10_000);
      await cola.agregar(posicion(s));
    }
    expect(cola.estado).toMatchObject({ pendientes: 6, error: 'sin_conexion' });
    expect(sesion.estado.fase).toBe('activa'); // la falta de red no cierra la sesión
    backend.sinRed = false;
    avanzar(70_000); // pasa la espera por fallos
    await cola.agregar(posicion(130));
    expect(cola.estado).toMatchObject({ pendientes: 0, error: null });
    expect(backend.posiciones.size).toBe(8);
  });

  it('reenviar un lote que sí llegó no duplica (se perdió la respuesta)', async () => {
    const backend = new BackendFalso();
    let perder = true;
    const http: typeof backend.http = async (url, init) => {
      const respuesta = await backend.http(url, init);
      if (perder && url.endsWith('/api/app/posiciones/')) {
        perder = false;
        throw new TypeError('respuesta perdida');
      }
      return respuesta;
    };
    const sesion = new SesionApp(http, almacenEnMemoria(), 'http://api.prueba');
    await sesion.login('conductor1@andes.example', 'clave');
    let reloj = 0;
    const cola = new ColaPosiciones(new Api(http, sesion), () => reloj);
    await cola.agregar(posicion(0));
    expect(cola.estado.pendientes).toBe(1);
    reloj += 5_000; // pasa la espera tras el primer fallo
    await cola.enviar();
    expect(backend.posiciones.size).toBe(1);
    expect(cola.estado.pendientes).toBe(0);
  });

  it('fuera de turno: vacía la cola y avisa para detener el GPS', async () => {
    const { backend, cola } = await armar();
    backend.enTurno = false;
    await cola.agregar(posicion(0));
    expect(cola.estado).toMatchObject({ pendientes: 0, detenido: 'fuera_de_turno' });
  });

  it('tope de pendientes: se descartan las más antiguas', async () => {
    const { backend, cola } = await armar();
    backend.sinRed = true;
    for (let i = 0; i < MAX_PENDIENTES + 5; i += 1) await cola.agregar(posicion(i));
    expect(cola.estado.pendientes).toBe(MAX_PENDIENTES);
  });

  it('al cerrar sesión no queda nada por enviar', async () => {
    const { backend, cola } = await armar();
    backend.sinRed = true;
    await cola.agregar(posicion(0));
    cola.vaciarSinEnviar();
    expect(cola.estado.pendientes).toBe(0);
  });
});

describe('rastreador', () => {
  function pluginFalso() {
    let entregar: ((p: Location) => void) | null = null;
    let fallar: ((e: { code?: string; message: string }) => void) | null = null;
    const plugin: Plugin & { activo: boolean } = {
      activo: false,
      async iniciar(alRecibir, alFallar) {
        entregar = alRecibir;
        fallar = alFallar as typeof fallar;
        this.activo = true;
        return 'w1';
      },
      async detener() {
        this.activo = false;
      },
    };
    return {
      plugin,
      entregar: (p: Partial<Location>) => entregar?.({ latitude: -33.4, longitude: -70.6, accuracy: 7.24, time: Date.now(), altitude: null, altitudeAccuracy: null, simulated: false, bearing: null, speed: null, ...p }),
      fallar: (code: string) => fallar?.({ code, message: code }),
    };
  }

  it('registra una posición cada 10 s en viaje aunque el plugin entregue cada 1 s', async () => {
    const { backend, cola, ahora, avanzar } = await armar();
    const falso = pluginFalso();
    const rastreador = new Rastreador(falso.plugin, cola, ahora);
    await rastreador.iniciar('viaje');
    for (let s = 0; s < 60; s += 1) {
      falso.entregar({ time: ahora() });
      avanzar(1000);
    }
    await cola.enviar();
    expect(backend.posiciones.size).toBe(6);
    expect([...backend.posiciones.values()][0]).toEqual({ lat: -33.4, lon: -70.6 });
    await rastreador.detener();
    expect(falso.plugin.activo).toBe(false);
  });

  it('en espera, una cada 30 s', async () => {
    const { backend, cola, ahora, avanzar } = await armar();
    const falso = pluginFalso();
    const rastreador = new Rastreador(falso.plugin, cola, ahora);
    await rastreador.iniciar('espera');
    for (let s = 0; s < 90; s += 1) {
      falso.entregar({ time: ahora() });
      avanzar(1000);
    }
    await cola.enviar();
    expect(backend.posiciones.size).toBe(3);
  });

  it('sin permiso de ubicación avisa', async () => {
    const { cola } = await armar();
    const falso = pluginFalso();
    const rastreador = new Rastreador(falso.plugin, cola);
    await rastreador.iniciar('espera');
    falso.fallar('NOT_AUTHORIZED');
    expect(rastreador.estado).toEqual({ activo: false, error: 'permiso' });
  });
});
