import { describe, expect, it, vi } from 'vitest';
import { ColaPosiciones } from './envio';
import type { CallbackError, Location } from './rastreo';
import { Rastreador, type Plugin } from './turno';

function crearCola() {
  return { agregar: vi.fn() } as unknown as ColaPosiciones;
}

describe('Rastreador de ubicación (RN-18)', () => {
  it('limpia el error de permiso si llegan posiciones al activar la ubicación', async () => {
    let alRecibir!: (pos: Location) => void;
    let alFallar!: (err: CallbackError) => void;
    const plugin: Plugin = {
      iniciar: vi.fn(async (ok, err) => {
        alRecibir = ok;
        alFallar = err;
        return 'w1';
      }),
      detener: vi.fn(async () => {}),
    };

    const rastreador = new Rastreador(plugin, crearCola(), () => 1_000_000);
    await rastreador.iniciar('espera');
    expect(rastreador.estado).toEqual({ activo: true, error: null });

    alFallar({ code: 'NOT_AUTHORIZED', message: 'Sin permiso' } as CallbackError);
    expect(rastreador.estado).toEqual({ activo: false, error: 'permiso' });

    alRecibir({ latitude: -33.45, longitude: -70.66, accuracy: 10, time: 1_000_000 } as Location);
    expect(rastreador.estado).toEqual({ activo: true, error: null });
  });

  it('reintenta el watcher tras un error de permiso y limpia la alerta si ya fue concedido', async () => {
    let alFallar!: (err: CallbackError) => void;
    const plugin: Plugin = {
      iniciar: vi.fn(async (_ok, err) => {
        alFallar = err;
        return 'w1';
      }),
      detener: vi.fn(async () => {}),
    };

    const rastreador = new Rastreador(plugin, crearCola());
    await rastreador.iniciar('espera');
    alFallar({ code: 'NOT_AUTHORIZED', message: 'Sin permiso' } as CallbackError);
    expect(rastreador.estado).toEqual({ activo: false, error: 'permiso' });

    await rastreador.reintentar();
    expect(plugin.detener).toHaveBeenCalledWith('w1');
    expect(plugin.iniciar).toHaveBeenCalledTimes(2);
    expect(rastreador.estado).toEqual({ activo: true, error: null });
  });

  it('no reinicia el watcher en reintentar() cuando no hay error', async () => {
    const plugin: Plugin = {
      iniciar: vi.fn(async () => 'w1'),
      detener: vi.fn(async () => {}),
    };

    const rastreador = new Rastreador(plugin, crearCola());
    await rastreador.iniciar('espera');
    await rastreador.reintentar();

    expect(plugin.detener).not.toHaveBeenCalled();
    expect(plugin.iniciar).toHaveBeenCalledTimes(1);
  });
});
