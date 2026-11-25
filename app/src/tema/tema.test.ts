/** CC-27 (HU-80, CP-74): el tema de la empresa en la app: se guarda en el celular y carga sin conexión. */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { descargarImagen } from './descargar';
import { CLAVE_TEMA, leerTema, TemaApp, type AparienciaEmpresa } from './tema';

const { pedido } = vi.hoisted(() => ({ pedido: vi.fn() }));
vi.mock('@capacitor/core', () => ({ CapacitorHttp: { request: pedido } }));

const EMPRESA = 'Transportes Andes Demo SpA';
const LOGO = 'data:image/png;base64,AAAA';
const con = (version: string): AparienciaEmpresa => ({ paleta: 'indigo', logo: { app: `/api/logo/${version}/app.png` } });

function almacen(inicial?: string) {
  const datos = new Map<string, string>(inicial ? [[CLAVE_TEMA, inicial]] : []);
  return { getItem: (c: string) => datos.get(c) ?? null, setItem: (c: string, v: string) => void datos.set(c, v) };
}

const raiz = () => ({ dataset: {} as Record<string, string> }) as unknown as HTMLElement;

afterEach(() => vi.unstubAllGlobals());

describe('tema de la empresa', () => {
  const conDocumento = () => {
    const cuerpo = raiz();
    vi.stubGlobal('document', { body: cuerpo });
    return cuerpo;
  };

  it('al ingresar aplica la paleta, descarga el logo y lo deja guardado', async () => {
    const cuerpo = conDocumento();
    const guardado = almacen();
    const descargar = vi.fn().mockResolvedValue(LOGO);
    const tema = new TemaApp(guardado, descargar, 'https://api.example');
    const avisos = vi.fn();
    tema.suscribir(avisos);

    await tema.actualizar(con('v1'), EMPRESA);

    expect(descargar).toHaveBeenCalledWith('https://api.example/api/logo/v1/app.png');
    expect(cuerpo.dataset.paleta).toBe('indigo');
    expect(leerTema(guardado)).toEqual({ paleta: 'indigo', empresa: EMPRESA, logo: LOGO, ruta: '/api/logo/v1/app.png' });
    expect(avisos).toHaveBeenCalled();
  });

  it('sin conexión, al abrir usa lo guardado sin pedir nada', () => {
    const guardado = almacen(JSON.stringify({ paleta: 'violeta', empresa: EMPRESA, logo: LOGO, ruta: '/x' }));
    const descargar = vi.fn();
    const tema = new TemaApp(guardado, descargar, '');
    const cuerpo = raiz();
    tema.aplicar(cuerpo);
    expect(cuerpo.dataset.paleta).toBe('violeta');
    expect(tema.leer()?.logo).toBe(LOGO);
    expect(descargar).not.toHaveBeenCalled();
  });

  it('el mismo logo no se descarga otra vez; uno nuevo sí', async () => {
    conDocumento();
    const descargar = vi.fn().mockResolvedValue(LOGO);
    const tema = new TemaApp(almacen(), descargar, '');
    await tema.actualizar(con('v1'), EMPRESA);
    await tema.actualizar(con('v1'), EMPRESA);
    expect(descargar).toHaveBeenCalledTimes(1);
    await tema.actualizar(con('v2'), EMPRESA);
    expect(descargar).toHaveBeenCalledTimes(2);
  });

  it('si el logo no se puede descargar usa el de FlotaÁgil y reintenta la próxima vez', async () => {
    conDocumento();
    const descargar = vi.fn().mockResolvedValueOnce(null).mockResolvedValue(LOGO);
    const tema = new TemaApp(almacen(), descargar, '');
    await tema.actualizar(con('v1'), EMPRESA);
    expect(tema.leer()).toMatchObject({ paleta: 'indigo', logo: null, ruta: null });
    await tema.actualizar(con('v1'), EMPRESA);
    expect(tema.leer()?.logo).toBe(LOGO);
  });

  it('al quitar el logo se borra el guardado; sin apariencia no cambia nada', async () => {
    conDocumento();
    const tema = new TemaApp(almacen(), vi.fn().mockResolvedValue(LOGO), '');
    await tema.actualizar(con('v1'), EMPRESA);
    await tema.actualizar(undefined, EMPRESA);
    expect(tema.leer()?.logo).toBe(LOGO);
    await tema.actualizar({ paleta: 'tiffany', logo: null }, EMPRESA);
    expect(tema.leer()).toMatchObject({ paleta: 'tiffany', logo: null });
  });

  it('un almacenamiento dañado o bloqueado no impide usar la app', async () => {
    conDocumento();
    expect(leerTema(almacen('no es json'))).toBeNull();
    expect(leerTema(null)).toBeNull();
    const bloqueado = {
      getItem: () => {
        throw new Error('bloqueado');
      },
      setItem: () => {
        throw new Error('lleno');
      },
    };
    const tema = new TemaApp(bloqueado, vi.fn(), '');
    await tema.actualizar({ paleta: 'cian', logo: null }, EMPRESA);
    expect(tema.leer()?.paleta).toBe('cian');
  });
});

describe('descarga del logo', () => {
  it('pide el archivo en binario y lo entrega como data URL', async () => {
    pedido.mockResolvedValue({ status: 200, data: 'AAAA\n' });
    expect(await descargarImagen('https://api.example/logo.png')).toBe(LOGO);
    expect(pedido).toHaveBeenCalledWith(expect.objectContaining({ url: 'https://api.example/logo.png', responseType: 'blob' }));
  });

  it('ante un error o sin red entrega null', async () => {
    pedido.mockResolvedValue({ status: 404, data: 'x' });
    expect(await descargarImagen('/logo.png')).toBeNull();
    pedido.mockRejectedValue(new Error('sin red'));
    expect(await descargarImagen('/logo.png')).toBeNull();
  });
});
