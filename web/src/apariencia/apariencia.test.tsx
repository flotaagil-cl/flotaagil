/** CC-27 (HU-78): pantalla «Apariencia» del panel (CP-72). */

import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import type { Apariencia } from '../diseno/LogoEmpresa';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { revisarArchivo } from './archivo';

const LOGO = {
  panel: '/api/publico/apariencia/transportes-andes/logo/v1/panel.png',
  portal: '/api/publico/apariencia/transportes-andes/logo/v1/portal.png',
  app: '/api/publico/apariencia/transportes-andes/logo/v1/app.png',
  correo: '/api/publico/apariencia/transportes-andes/logo/v1/correo.png',
  icono: '/api/publico/apariencia/transportes-andes/logo/v1/icono.png',
};

class ServidorAparienciaFalso {
  datos: Apariencia = { paleta: 'tiffany', logo: null };
  llamadas: string[] = [];
  siguiente: Respuesta | null = null;
  private readonly anterior: ServidorAuthFalso['api'];

  constructor(auth: ServidorAuthFalso) {
    this.anterior = auth.api;
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    if (!url.pathname.startsWith('/api/apariencia/')) return this.anterior!(peticion, url);
    const ruta = `${peticion.method} ${url.pathname}`;
    if (peticion.method !== 'GET') {
      if (this.siguiente) {
        this.llamadas.push(ruta);
        return this.siguiente;
      }
      if (ruta === 'PATCH /api/apariencia/') {
        const cuerpo = JSON.parse(await peticion.text()) as { paleta: Apariencia['paleta'] };
        this.llamadas.push(`${ruta} ${cuerpo.paleta}`);
        this.datos = { ...this.datos, paleta: cuerpo.paleta };
      } else {
        this.llamadas.push(ruta);
        this.datos = { ...this.datos, logo: peticion.method === 'DELETE' ? null : LOGO };
      }
    }
    return { estado: 200, cuerpo: this.datos };
  }
}

function montar(ruta = '/apariencia', email = 'admin@andes.example') {
  const contexto = montarPanel(ruta, { email });
  return { ...contexto, apariencia: new ServidorAparienciaFalso(contexto.servidor) };
}

// Como en la carga por CSV: FormData y File de Node, para que el Request sepa armar el multipart.
const CRLF = String.fromCharCode(13, 10);
const originales = { FormData: globalThis.FormData, File: globalThis.File };
beforeAll(async () => {
  const multipart = ['--x', 'Content-Disposition: form-data; name="f"; filename="a.txt"', '', 'hola', '--x--', ''].join(CRLF);
  const formulario = await new Response(multipart, { headers: { 'Content-Type': 'multipart/form-data; boundary=x' } }).formData();
  Object.assign(globalThis, { FormData: formulario.constructor, File: (formulario.get('f') as object).constructor });
});
afterAll(() => {
  Object.assign(globalThis, originales);
});

// jsdom no puede crear la URL local del archivo elegido.
beforeEach(() => {
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:vista-del-logo');
  vi.spyOn(URL, 'revokeObjectURL').mockReturnValue(undefined);
});

const marco = () => document.querySelector('.tema-flotaagil')!;
const imagen = (tipo = 'image/png', bytes = 10) => new File([new Uint8Array(bytes)], 'logo.png', { type: tipo });

describe('permisos', () => {
  it('el administrador la ve en el menú, junto a Usuarios', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Apariencia' })).toHaveAttribute('href', '/apariencia');
  });

  it('el despachador no la ve y por URL no consulta la API', async () => {
    const { servidor } = montar('/apariencia', 'despacho@andes.example');
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Apariencia' })).not.toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes('/api/apariencia/'))).toBe(false);
  });
});

describe('paleta', () => {
  it('muestra las 10 con su nombre; la vista previa cambia al elegir y el panel solo al guardar, sin recargar', async () => {
    const { apariencia } = montar();
    const grupo = await screen.findByRole('group', { name: 'Paleta de colores' });
    expect(within(grupo).getAllByRole('radio')).toHaveLength(10);
    expect(within(grupo).getByRole('radio', { name: /Tiffany.*predeterminada/ })).toBeChecked();
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled();

    await userEvent.click(within(grupo).getByRole('radio', { name: 'Índigo' }));
    expect(screen.getByTestId('vista-previa')).toHaveAttribute('data-paleta', 'indigo');
    expect(marco()).toHaveAttribute('data-paleta', 'tiffany'); // aún sin guardar
    expect(apariencia.llamadas).toEqual([]);

    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument();
    expect(apariencia.llamadas).toEqual(['PATCH /api/apariencia/ indigo']);
    await waitFor(() => expect(marco()).toHaveAttribute('data-paleta', 'indigo'));
  });

  it('«Restablecer a Tiffany» guarda la predeterminada', async () => {
    const contexto = montarPanel('/apariencia', { email: 'admin@andes.example' });
    const apariencia = new ServidorAparienciaFalso(contexto.servidor);
    apariencia.datos = { paleta: 'grafito', logo: null };
    await userEvent.click(await screen.findByRole('button', { name: 'Restablecer a Tiffany' }));
    await waitFor(() => expect(apariencia.llamadas).toEqual(['PATCH /api/apariencia/ tiffany']));
    expect(await screen.findByRole('radio', { name: /Tiffany/ })).toBeChecked();
  });

  it('la vista previa muestra los estados con ícono y texto', async () => {
    montar();
    const vista = await screen.findByTestId('vista-previa');
    for (const texto of ['Solicitado', 'En camino', 'Cancelado']) {
      expect(within(vista).getByText(texto).querySelector('svg')).not.toBeNull();
    }
  });
});

describe('logo', () => {
  it('sube el logo, lo aplica en el encabezado del panel y se puede quitar', async () => {
    const { apariencia } = montar();
    expect(await screen.findByText('Sin logo propio: se usa el de FlotaÁgil.')).toBeInTheDocument();
    await userEvent.upload(screen.getByLabelText('Subir un logo'), imagen());
    expect(screen.getByRole('img', { name: 'Vista previa del logo nuevo' })).toHaveAttribute('src', 'blob:vista-del-logo');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    await screen.findByText('Cambios guardados.');
    expect(apariencia.llamadas).toEqual(['POST /api/apariencia/logo/']);
    const cabecera = document.querySelector('header')!;
    await waitFor(() => expect(within(cabecera).getByRole('img', { name: 'Logo de Transportes Andes Demo SpA' })).toHaveAttribute('src', LOGO.panel));

    await userEvent.click(screen.getByRole('button', { name: 'Quitar el logo' }));
    expect(await screen.findByText(/Se quitó el logo/)).toBeInTheDocument();
    await waitFor(() => expect(within(cabecera).queryByRole('img')).not.toBeInTheDocument());
    expect(within(cabecera).getByText('FlotaÁgil')).toBeInTheDocument();
  });

  it('avisa antes de subir un tipo no admitido y no lo envía', async () => {
    const { apariencia } = montar();
    const campo = await screen.findByLabelText('Subir un logo');
    // userEvent respeta `accept`: el cambio se dispara directo, como al arrastrar un archivo.
    fireEvent.change(campo, { target: { files: [imagen('image/svg+xml')] } });
    expect(await screen.findByText('El logo debe ser una imagen PNG, JPG o WebP.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Guardar cambios' })).toBeDisabled();
    expect(apariencia.llamadas).toEqual([]);
  });

  it('muestra el motivo del servidor si lo rechaza', async () => {
    const { apariencia } = montar();
    apariencia.siguiente = { estado: 400, cuerpo: { logo: ['El logo debe medir al menos 256 px de ancho (mide 200 px).'] } };
    await userEvent.upload(await screen.findByLabelText('Subir un logo'), imagen());
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText(/mide 200 px/)).toBeInTheDocument();
    expect(screen.queryByText('Cambios guardados.')).not.toBeInTheDocument();
  });

  it.each([
    ['image/png', 10, null],
    ['image/webp', 10, null],
    ['image/gif', 10, 'El logo debe ser una imagen PNG, JPG o WebP.'],
    ['image/png', 2 * 1024 * 1024 + 1, 'El logo pesa más de 2 MB.'],
  ])('revisa tipo y peso: %s de %i bytes', (tipo, bytes, esperado) => {
    expect(revisarArchivo(imagen(tipo, bytes))).toBe(esperado);
  });
});

describe('el despachador ve el resultado', () => {
  it('su panel toma la paleta y el logo de la sesión', async () => {
    const contexto = montarPanel('/', { email: 'despacho@andes.example' });
    contexto.servidor.apariencia = { paleta: 'violeta', logo: LOGO };
    contexto.recargar();
    await waitFor(() => expect(document.querySelector('.tema-flotaagil')).toHaveAttribute('data-paleta', 'violeta'));
    expect(screen.getByRole('img', { name: 'Logo de Transportes Andes Demo SpA' })).toBeInTheDocument();
  });
});
