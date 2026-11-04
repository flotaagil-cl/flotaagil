import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { conTiempoLimite, TIEMPO_LIMITE_MS, TiempoAgotado } from './http';

const nunca = () => new Promise<Response>(() => {});

describe('tiempo límite de las peticiones', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('son 10 s', () => {
    expect(TIEMPO_LIMITE_MS).toBe(10_000);
  });

  it('devuelve la respuesta con su estado, cuerpo y encabezados', async () => {
    const http = conTiempoLimite(async () => new Response('{"a":1}', { status: 201, headers: { 'X-Uno': '1' } }));
    const respuesta = await http('https://x.example/', {});
    expect(respuesta.status).toBe(201);
    expect(respuesta.headers.get('X-Uno')).toBe('1');
    expect(await respuesta.json()).toEqual({ a: 1 });
  });

  it('admite respuestas sin cuerpo', async () => {
    const respuesta = await conTiempoLimite(async () => new Response(null, { status: 204 }))('https://x.example/', {});
    expect(respuesta.status).toBe(204);
  });

  it('corta a los 10 s y aborta la señal, aunque el fetch nativo la ignore', async () => {
    let senal: AbortSignal | null | undefined;
    const http = conTiempoLimite((_, init) => {
      senal = init.signal;
      return nunca();
    });
    let resultado: unknown = 'pendiente';
    http('https://x.example/', {}).catch((error: unknown) => {
      resultado = error;
    });
    await vi.advanceTimersByTimeAsync(9_999);
    expect(resultado).toBe('pendiente');
    expect(senal?.aborted).toBe(false);
    await vi.advanceTimersByTimeAsync(1);
    expect(resultado).toBeInstanceOf(TiempoAgotado);
    expect(senal?.aborted).toBe(true);
  });

  it('también corta si el cuerpo se queda a medias', async () => {
    const atascada = new Response(new ReadableStream({ start() {} }));
    const promesa = conTiempoLimite(async () => atascada)('https://x.example/', {});
    const espera = expect(promesa).rejects.toBeInstanceOf(TiempoAgotado);
    await vi.advanceTimersByTimeAsync(TIEMPO_LIMITE_MS);
    await espera;
  });

  it('un error de red se propaga y no deja el temporizador corriendo', async () => {
    const http = conTiempoLimite(async () => {
      throw new TypeError('Failed to fetch');
    });
    await expect(http('https://x.example/', {})).rejects.toBeInstanceOf(TypeError);
    expect(vi.getTimerCount()).toBe(0);
  });
});
