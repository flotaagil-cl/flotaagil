import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SinRed, SinSesion } from '../sesion/sesion';
import { Recarga } from './recarga';

function preparar() {
  const pendientes: { resolver: (v: string) => void; rechazar: (e: unknown) => void }[] = [];
  const aplicados: string[] = [];
  const fallas: unknown[] = [];
  const recarga = new Recarga<string>(
    () => new Promise((resolver, rechazar) => pendientes.push({ resolver, rechazar })),
    (datos) => aplicados.push(datos),
    (error) => fallas.push(error),
  );
  return { recarga, pendientes, aplicados, fallas };
}

describe('recarga', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it('una respuesta atrasada no pisa a la más nueva', async () => {
    const { recarga, pendientes, aplicados } = preparar();
    const vieja = recarga.recargar();
    const nueva = recarga.recargar();
    pendientes[1].resolver('nueva');
    await nueva;
    pendientes[0].resolver('vieja');
    await vieja;
    expect(aplicados).toEqual(['nueva']);
  });

  it('una falla atrasada no programa un reintento', async () => {
    const { recarga, pendientes, fallas } = preparar();
    const vieja = recarga.recargar();
    const nueva = recarga.recargar();
    pendientes[1].resolver('nueva');
    await nueva;
    pendientes[0].rechazar(new SinRed());
    await vieja;
    expect(fallas).toEqual([]);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('reintenta solo, con espera creciente, hasta lograrlo', async () => {
    const { recarga, pendientes, aplicados, fallas } = preparar();
    const primera = recarga.recargar();
    pendientes[0].rechazar(new SinRed());
    await primera;
    expect(fallas).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1_999);
    expect(pendientes).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(pendientes).toHaveLength(2);
    pendientes[1].rechazar(new SinRed());
    await vi.advanceTimersByTimeAsync(3_999);
    expect(pendientes).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(pendientes).toHaveLength(3);
    pendientes[2].resolver('listo');
    await vi.advanceTimersByTimeAsync(0);
    expect(aplicados).toEqual(['listo']);
    expect(vi.getTimerCount()).toBe(0);
  });

  it('la espera no pasa de 30 s', async () => {
    const { recarga, pendientes } = preparar();
    void recarga.recargar();
    for (let i = 0; i < 6; i += 1) {
      pendientes[i].rechazar(new SinRed());
      await vi.advanceTimersByTimeAsync(0);
      await vi.advanceTimersByTimeAsync(30_000);
    }
    expect(pendientes).toHaveLength(7);
  });

  it('sin sesión no reintenta', async () => {
    const { recarga, pendientes } = preparar();
    const lectura = recarga.recargar();
    pendientes[0].rechazar(new SinSesion());
    await lectura;
    expect(vi.getTimerCount()).toBe(0);
  });

  it('al detenerla no aplica lo que estaba en curso ni reintenta', async () => {
    const { recarga, pendientes, aplicados } = preparar();
    const lectura = recarga.recargar();
    recarga.detener();
    pendientes[0].resolver('tarde');
    await lectura;
    expect(aplicados).toEqual([]);
    await recarga.recargar();
    expect(pendientes).toHaveLength(1);
    recarga.iniciar();
    void recarga.recargar();
    expect(pendientes).toHaveLength(2);
  });

  it('una lectura nueva cancela el reintento pendiente', async () => {
    const { recarga, pendientes, aplicados } = preparar();
    const primera = recarga.recargar();
    pendientes[0].rechazar(new SinRed());
    await primera;
    const nueva = recarga.recargar();
    pendientes[1].resolver('ok');
    await nueva;
    expect(aplicados).toEqual(['ok']);
    expect(vi.getTimerCount()).toBe(0);
  });
});
