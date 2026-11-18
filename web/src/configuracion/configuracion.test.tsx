/** DC-68: configuración de la empresa en el panel, solo el administrador. */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';

const RUTA = '/api/configuracion-empresa/';

class ServidorConfiguracionFalso {
  datos: Record<string, unknown> = {
    telefono_central: '',
    whatsapp_central: '+56999900000',
    confirmacion_antes_horas: 24,
    confirmacion_plazo_corto_min: 60,
    cierre_no_confirmada_horas: 2,
    reserva_publica_max_ip_hora: 20,
    reserva_publica_max_correo_hora: 5,
    reserva_publica_max_convenio_hora: 50,
  };
  cuerpos: unknown[] = [];
  siguiente: Respuesta | null = null;
  private readonly anterior: ServidorAuthFalso['api'];

  constructor(auth: ServidorAuthFalso) {
    this.anterior = auth.api;
    auth.api = (peticion, url) => this.atender(peticion, url);
  }

  private async atender(peticion: Request, url: URL): Promise<Respuesta> {
    if (url.pathname !== RUTA) return this.anterior!(peticion, url);
    if (peticion.method === 'PATCH') {
      const cuerpo = JSON.parse(await peticion.text());
      this.cuerpos.push(cuerpo);
      if (this.siguiente) return this.siguiente;
      this.datos = { ...this.datos, ...cuerpo, telefono_central: String(cuerpo.telefono_central).replace(/\s/g, '') };
    }
    return { estado: 200, cuerpo: this.datos };
  }
}

function montar(ruta = '/configuracion', email = 'admin@andes.example') {
  const contexto = montarPanel(ruta, { email });
  return { ...contexto, config: new ServidorConfiguracionFalso(contexto.servidor) };
}

describe('permisos', () => {
  it('el administrador la ve en el menú', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Configuración' })).toBeInTheDocument();
  });

  it('el despachador no, y por URL ve «sin permiso» sin consultar la API', async () => {
    const { servidor } = montar('/configuracion', 'despacho@andes.example');
    expect(await screen.findByRole('heading', { name: /permiso/i })).toBeInTheDocument();
    expect(servidor.urls.some((u) => u.includes(RUTA))).toBe(false);
  });
});

describe('formulario', () => {
  it('muestra los valores y guarda los números de la central', async () => {
    const { config } = montar();
    const telefono = await screen.findByLabelText('Teléfono de la central');
    expect(screen.getByLabelText('WhatsApp de la central')).toHaveValue('+56999900000');
    expect(screen.getByLabelText(/Plazo para confirmar/)).toHaveValue(24);
    expect(screen.getByText(/Entre 1 y 168/)).toBeInTheDocument();
    await userEvent.type(telefono, '+56 2 2999 0000');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument();
    expect(config.cuerpos[0]).toMatchObject({ telefono_central: '+56 2 2999 0000', confirmacion_antes_horas: 24 });
    expect(config.cuerpos[0]).not.toHaveProperty('modulo_cuentas');
  });

  it('fuera de rango no envía y explica el límite', async () => {
    const { config } = montar();
    const campo = await screen.findByLabelText(/Cierre de las «Sin confirmar»/);
    await userEvent.clear(campo);
    await userEvent.type(campo, '72');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    expect(screen.getByText('Debe ser un número entero entre 1 y 48.')).toBeInTheDocument();
    expect(config.cuerpos).toEqual([]);
  });

  it.each([
    ['1', '60', true],
    ['1', '59', false],
  ])('con %s h de plazo, un plazo corto de %s min %s', async (horas, corto, rechaza) => {
    const { config } = montar();
    const plazo = await screen.findByLabelText(/Plazo para confirmar/);
    await userEvent.clear(plazo);
    await userEvent.type(plazo, horas);
    const campo = screen.getByLabelText('Plazo corto (minutos)');
    await userEvent.clear(campo);
    await userEvent.type(campo, corto);
    await userEvent.click(screen.getByRole('button', { name: 'Guardar cambios' }));
    if (rechaza) {
      expect(screen.getByText('Debe ser menor que el plazo para confirmar (1 h = 60 min).')).toBeInTheDocument();
      expect(config.cuerpos).toEqual([]);
    } else {
      expect(await screen.findByText('Cambios guardados.')).toBeInTheDocument();
    }
  });

  it('el mínimo por conexión es 5', async () => {
    montar();
    expect(await screen.findByText(/Antispam del formulario público\. Entre 5 y 500\./)).toBeInTheDocument();
  });

  it('muestra el error del servidor en su campo', async () => {
    const { config } = montar();
    config.siguiente = { estado: 400, cuerpo: { whatsapp_central: ['Número en formato internacional, p. ej. +56912345678.'] } };
    await userEvent.click(await screen.findByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByText(/Número en formato internacional/)).toBeInTheDocument();
    expect(screen.queryByText('Cambios guardados.')).not.toBeInTheDocument();
  });

  it('un error sin campos muestra un aviso general', async () => {
    const { config } = montar();
    config.siguiente = { estado: 500, cuerpo: {} };
    await userEvent.click(await screen.findByRole('button', { name: 'Guardar cambios' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No se pudo guardar.');
  });
});
