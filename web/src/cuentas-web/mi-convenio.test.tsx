/** HU-34: cuenta del convenio en la web y registro público de la empresa. */

import { screen, waitFor } from '@testing-library/react';
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

function instalar(auth: ServidorAuthFalso, convenio: Record<string, unknown>) {
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
          results: [{ id: 3, estado: 'SOLICITADO', estado_texto: 'Solicitado', pasajero: 'Pedro Pasajero', origen_dir: 'A', destino_dir: 'B', recogida_en: '2026-10-30T17:00:00Z' }],
        },
      };
    }
    if (url.pathname === '/api/portal/transportes-andes/') return { estado: 200, cuerpo: EMPRESA_PORTAL };
    if (url.pathname === '/api/mi-convenio/solicitudes/') {
      recibidas.push(await peticion.json());
      return { estado: 201, cuerpo: { estado: 'SOLICITADO', recogida_en: '2026-10-30T17:00:00Z', expira_en: null, mensaje: 'Recibimos la solicitud.' } };
    }
    return anterior!(peticion, url);
  };
  return recibidas;
}

describe('cuenta del convenio', () => {
  it('en revisión: ve el aviso y no el formulario', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    instalar(servidor, { ...CONVENIO, estado: 'EN_REVISION' });
    expect(await screen.findByText(/Tu registro está en revisión/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Solicitar viaje/ })).not.toBeInTheDocument();
  });

  it('rechazado: ve el motivo', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    instalar(servidor, { ...CONVENIO, estado: 'RECHAZADO', motivo_rechazo: 'RUT no corresponde' });
    expect(await screen.findByText(/Motivo: RUT no corresponde/)).toBeInTheDocument();
  });

  it('aprobado: ve sus reservas y el formulario con la declaración, sin nombre de supervisor', async () => {
    const { servidor } = montarPanel('/mi-convenio', { email: 'convenio@andes.example' });
    instalar(servidor, CONVENIO);
    expect(await screen.findByRole('table', { name: 'Reservas del convenio' })).toBeInTheDocument();
    expect(screen.getByText('Pedro Pasajero')).toBeInTheDocument();
    expect(await screen.findByLabelText(/Declaro que el pasajero autorizó/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Nombre del supervisor')).not.toBeInTheDocument();
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
