/** HU-34 y HU-46: cuenta del convenio en la web (marco del portal) y registro público de la empresa. */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { montarPanel } from '../pruebas/montar';
import { EMPRESA_PORTAL, ServidorPortalFalso } from '../pruebas/servidorPortalFalso';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { crearRutas } from '../rutas/tabla';

const CONVENIO = {
  id: 9,
  cliente_nombre: 'Minera Norte',
  cliente_rut: '76543210-3',
  direccion: 'Av. Apoquindo 3000',
  encargado_nombre: 'Clara Cliente',
  encargado_telefono: '+56900008001',
  estado: 'APROBADO',
  motivo_rechazo: null,
  empresa: 'Transportes Andes Demo SpA',
  empresa_slug: 'transportes-andes',
};

function instalar(auth: ServidorAuthFalso, convenio: Record<string, unknown>, central = { telefono: null as string | null, whatsapp: null as string | null }) {
  const anterior = auth.api;
  const recibidas: unknown[] = [];
  auth.api = async (peticion: Request, url: URL): Promise<Respuesta> => {
    if (url.pathname === '/api/mi-convenio/') return { estado: 200, cuerpo: convenio };
    if (url.pathname === '/api/mi-convenio/reservas/') {
      return {
        estado: 200,
        cuerpo: {
          count: 1,
          next: null,
          previous: null,
          results: [{ id: 3, estado: 'SOLICITADO', estado_texto: 'Solicitado', pasajero: 'Pedro Pasajero', sentido: 'URBANO', origen_dir: 'A', destino_dir: 'B', recogida_en: '2030-10-30T17:00:00Z' }],
        },
      };
    }
    if (url.pathname === '/api/portal/transportes-andes/') return { estado: 200, cuerpo: { ...EMPRESA_PORTAL, central } };
    if (url.pathname === '/api/mi-convenio/solicitudes/') {
      recibidas.push(await peticion.json());
      return { estado: 201, cuerpo: { estado: 'SOLICITADO', recogida_en: '2026-10-30T17:00:00Z', expira_en: null, mensaje: 'Recibimos la solicitud.' } };
    }
    return anterior!(peticion, url);
  };
  return recibidas;
}

describe('cuenta del convenio (HU-46)', () => {
  it('en revisión: tarjeta con la insignia, sin formulario y con el contacto de la central', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    instalar(servidor, { ...CONVENIO, estado: 'EN_REVISION' }, { telefono: '+56999900001', whatsapp: null });
    expect(await screen.findByText(/Tu registro está en revisión/)).toBeInTheDocument();
    expect(screen.getByText('En revisión')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Siguiente: quién viaja/ })).not.toBeInTheDocument();
    // HU-49 (DC-80): sin WhatsApp propio, el botón usa el teléfono de la central.
    expect(await screen.findByRole('link', { name: 'WhatsApp de la central' })).toHaveAttribute('href', 'https://wa.me/56999900001');
  });

  it('rechazado: insignia y motivo', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    instalar(servidor, { ...CONVENIO, estado: 'RECHAZADO', motivo_rechazo: 'RUT no corresponde' });
    expect(await screen.findByText('Motivo: RUT no corresponde')).toBeInTheDocument();
    expect(screen.getByText('Rechazado')).toBeInTheDocument();
  });

  it('usa el marco del portal (sin el menú del panel) y nada de WhatsApp en el pedido', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    instalar(servidor, CONVENIO);
    expect(await screen.findByRole('heading', { name: '¿A dónde llevamos a tu equipo?' })).toBeInTheDocument();
    const principal = screen.getByRole('navigation', { name: 'Principal' });
    expect(within(principal).getByRole('link', { name: 'Viajes del convenio' })).toHaveAttribute('href', '/mi-convenio/viajes');
    expect(screen.queryByText(/WhatsApp/)).not.toBeInTheDocument();
  });

  it('pide: viaje, quién viaja con la declaración de privacidad y pedido recibido', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    const recibidas = instalar(servidor, CONVENIO);
    await userEvent.click(await screen.findByRole('tab', { name: 'En la ciudad' }));
    await userEvent.type(await screen.findByLabelText('Origen'), 'Av. Providencia 1208');
    await userEvent.type(screen.getByLabelText('Destino'), 'Plaza de Armas');
    await userEvent.click(screen.getByRole('button', { name: 'Siguiente: quién viaja' }));
    expect(await screen.findByRole('heading', { name: 'Quién viaja' })).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar pedido' }));
    expect(screen.getByLabelText('Nombre del pasajero')).toHaveAccessibleDescription('Escribe el nombre del pasajero.');
    expect(recibidas).toHaveLength(0);
    await userEvent.type(screen.getByLabelText('Nombre del pasajero'), 'Pedro Pasajero');
    await userEvent.type(screen.getByLabelText('Teléfono del pasajero'), '+56900008003');
    await userEvent.click(screen.getByLabelText(/Declaro que informé al pasajero/));
    await userEvent.click(screen.getByRole('button', { name: 'Confirmar pedido' }));
    expect(await screen.findByRole('heading', { name: '¡Listo! Recibimos el pedido' })).toBeInTheDocument();
    expect(recibidas[0]).toMatchObject({ nombre: 'Pedro Pasajero', telefono: '+56900008003', declara_informados: true, sentido: 'URBANO' });
    expect(recibidas[0]).not.toHaveProperty('acepta_whatsapp');
    expect(screen.getByRole('link', { name: 'Ver los viajes del convenio' })).toHaveAttribute('href', '/mi-convenio/viajes');
  });

  it('viajes del convenio: tarjetas con el pasajero, la insignia y el número', async () => {
    const { servidor } = montarPanel('/mi-convenio/viajes', { email: 'convenio@andes.example' });
    instalar(servidor, CONVENIO);
    const proximos = await screen.findByRole('region', { name: 'Próximos' });
    expect(within(proximos).getByText('A → B')).toBeInTheDocument();
    expect(within(proximos).getByText(/Pedro Pasajero · .* · N\.º 3/)).toBeInTheDocument();
    expect(within(proximos).getByText('Buscando conductor')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('otro rol no entra a la cuenta del convenio', async () => {
    const { router } = montarPanel('/mi-convenio', { email: 'pasajero@andes.example' });
    await waitFor(() => expect(router.state.location.pathname).toBe('/pedir'));
  });
});

describe('registro de empresa en el portal', () => {
  function montarRegistro() {
    const servidor = new ServidorPortalFalso();
    const { entorno } = crearEntorno({ servidor, locks: crearLocks(), ahora: servidor.ahora });
    const rutas = crearRutas();
    const router = createMemoryRouter(rutas, { initialEntries: ['/solicitar/transportes-andes/registro-empresa'] });
    render(<App entorno={entorno} rutas={rutas} router={router} />);
    return servidor;
  }

  const llenar = async (cambios: Record<string, string> = {}) => {
    const valores: Record<string, string> = {
      'Razón social': 'Constructora Sintética SpA',
      'RUT de la empresa': '76543210-3',
      'Dirección': 'Av. Apoquindo 3000',
      'Nombre del encargado': 'Elena Encargada',
      'Correo del encargado': 'elena@constructora.example',
      'Teléfono del encargado': '+56900008001',
      'Contraseña': 'Clave-Sintetica-2026',
      ...cambios,
    };
    for (const [etiqueta, valor] of Object.entries(valores)) {
      if (valor) await userEvent.type(await screen.findByLabelText(etiqueta), valor);
    }
  };

  it('envía y queda en revisión', async () => {
    const servidor = montarRegistro();
    await llenar();
    await userEvent.click(screen.getByRole('button', { name: 'Registrar empresa' }));
    expect(await screen.findByRole('heading', { name: 'Registro recibido' })).toBeInTheDocument();
    expect(servidor.registros[0]).toMatchObject({ cliente_nombre: 'Constructora Sintética SpA', email: 'elena@constructora.example', sitio_web: '' });
  });

  it('valida antes de enviar', async () => {
    const servidor = montarRegistro();
    await llenar({ 'Correo del encargado': 'no-es-correo', 'Contraseña': 'corta' });
    await userEvent.click(screen.getByRole('button', { name: 'Registrar empresa' }));
    expect(screen.getByText('Ingresa un correo válido.')).toBeInTheDocument();
    expect(screen.getByText('Mínimo 10 caracteres.')).toBeInTheDocument();
    expect(servidor.registros).toEqual([]);
  });

  it('un error del servidor queda en su campo', async () => {
    const servidor = montarRegistro();
    servidor.siguiente({ estado: 400, cuerpo: { email: ['No se pudo registrar con ese correo.'] } });
    await llenar();
    await userEvent.click(screen.getByRole('button', { name: 'Registrar empresa' }));
    await waitFor(() => expect(screen.getByText('No se pudo registrar con ese correo.')).toBeInTheDocument());
  });
});
