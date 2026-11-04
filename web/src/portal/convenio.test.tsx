/** HU-25: link del convenio con contraseña (CP-26, RN-07, RN-08), con el backend falso y sin la sesión del panel. */

import { fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { ServidorConvenioFalso, TOKEN } from '../pruebas/servidorConvenioFalso';
import { crearRutas } from '../rutas/tabla';

const DECLARACION = 'Declaro que el pasajero autorizó recibir avisos por WhatsApp';

function montar(servidor = new ServidorConvenioFalso()) {
  const locks = crearLocks();
  const { entorno } = crearEntorno({ servidor: servidor as never, locks, ahora: servidor.ahora });
  const rutas = crearRutas();
  const router = createMemoryRouter(rutas, { initialEntries: [`/convenio/${TOKEN}`] });
  render(<App entorno={entorno} rutas={rutas} router={router} />);
  return { servidor, locks };
}

async function intentar(password: string) {
  const usuario = userEvent.setup();
  await usuario.type(await screen.findByLabelText('Contraseña'), password);
  await usuario.click(screen.getByRole('button', { name: 'Entrar' }));
}

async function llenarYEnviar(declarar = true) {
  const usuario = userEvent.setup();
  await usuario.type(screen.getByLabelText('Nombre'), 'Ana Pasajera');
  await usuario.type(screen.getByLabelText('WhatsApp'), '+56 9 8765 4321');
  await usuario.type(screen.getByLabelText('Dirección de origen'), 'Av. Providencia 1234');
  await usuario.type(screen.getByLabelText('Dirección de destino'), 'Plaza de Armas');
  fireEvent.change(screen.getByLabelText(/^Recogida/), { target: { value: '2026-10-30T14:00' } });
  await usuario.click(screen.getByLabelText('Acepto el aviso de privacidad.'));
  await usuario.click(screen.getByLabelText(/^Acepto recibir por WhatsApp/));
  if (declarar) {
    await usuario.click(screen.getByLabelText(DECLARACION));
    await usuario.type(screen.getByLabelText('Nombre del supervisor'), '  Sara Supervisora  ');
  }
  await usuario.click(screen.getByRole('button', { name: 'Solicitar viaje' }));
}

const conSesion = () => {
  const servidor = new ServidorConvenioFalso();
  servidor.sesion = true;
  return servidor;
};

describe('contraseña', () => {
  it('el link pide la contraseña y no revela el cliente ni el formulario', async () => {
    const { servidor, locks } = montar();
    expect(await screen.findByRole('heading', { name: 'Acceso de convenio' })).toBeInTheDocument();
    expect(screen.queryByText(/Minera Sintética/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Nombre')).not.toBeInTheDocument();
    expect(servidor.prohibidas).toEqual([]);
    expect(locks.solicitudes).toBe(0);
  });

  it('sin escribirla no se envía', async () => {
    montar();
    await screen.findByLabelText('Contraseña');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
    expect(await screen.findByText('Ingresa la contraseña.')).toBeInTheDocument();
  });

  it('la correcta lleva al formulario con el convenio', async () => {
    montar();
    await intentar('ClaveSintetica23');
    expect(await screen.findByRole('heading', { name: 'Solicitar un viaje' })).toBeInTheDocument();
    expect(within(screen.getByRole('banner')).getByText('Convenio Minera Sintética S.A.')).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Datos del pasajero' })).toBeInTheDocument();
  });

  it('la incorrecta lo dice, limpia el campo y no entra', async () => {
    montar();
    await intentar('mala');
    expect(await screen.findByText('La contraseña no es correcta.')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toHaveValue('');
    expect(screen.queryByLabelText('Nombre')).not.toBeInTheDocument();
  });

  it('al quinto intento informa el bloqueo, y sigue bloqueado con la correcta', async () => {
    const { servidor } = montar();
    for (let i = 0; i < 5; i += 1) await intentar('mala');
    expect(await screen.findByText(/quedó bloqueado por intentos fallidos/)).toBeInTheDocument();
    expect(servidor.bloqueado).toBe(true);
    await intentar('ClaveSintetica23');
    expect(await screen.findByText(/quedó bloqueado/)).toBeInTheDocument();
    expect(screen.queryByLabelText('Nombre')).not.toBeInTheDocument();
  });
});

describe('link no disponible (RN-08)', () => {
  it('convenio desactivado o inexistente: página clara', async () => {
    const servidor = new ServidorConvenioFalso();
    servidor.activo = false;
    montar(servidor);
    expect(await screen.findByRole('heading', { name: 'Este link de convenio no está disponible' })).toBeInTheDocument();
    expect(screen.queryByLabelText('Contraseña')).not.toBeInTheDocument();
  });

  it('desactivado con la sesión abierta: al enviar deja de funcionar', async () => {
    const servidor = conSesion();
    servidor.desactivarAlEnviar = true;
    montar(servidor);
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await llenarYEnviar();
    expect(await screen.findByRole('heading', { name: 'Este link de convenio no está disponible' })).toBeInTheDocument();
  });

  it('sin red ofrece reintentar', async () => {
    const servidor = new ServidorConvenioFalso();
    servidor.fallaAcceso = 'red';
    montar(servidor);
    const boton = await screen.findByRole('button', { name: 'Reintentar' });
    servidor.fallaAcceso = null;
    await userEvent.click(boton);
    expect(await screen.findByLabelText('Contraseña')).toBeInTheDocument();
  });
});

describe('reserva (RN-07)', () => {
  it('queda registrada sin pedir confirmación por WhatsApp', async () => {
    const { servidor } = montar(conSesion());
    expect(await screen.findByText(/sin confirmación por WhatsApp/)).toBeInTheDocument();
    await llenarYEnviar();
    expect(await screen.findByRole('heading', { name: 'Solicitud recibida' })).toBeInTheDocument();
    expect(screen.getByText(/No requiere confirmación por WhatsApp/)).toBeInTheDocument();
    expect(screen.queryByText(/Confirma respondiendo/)).not.toBeInTheDocument();
    expect(servidor.cuerpos).toHaveLength(1);
    expect(servidor.cuerpos[0].nombre).toBe('Ana Pasajera');
  });

  it('envía la declaración y el nombre del supervisor', async () => {
    const { servidor } = montar(conSesion());
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await llenarYEnviar();
    await screen.findByRole('heading', { name: 'Solicitud recibida' });
    expect(servidor.cuerpos[0]).toMatchObject({ supervisor: 'Sara Supervisora', declara_autorizacion: true });
  });

  it('sin la declaración ni el nombre no se envía', async () => {
    const { servidor } = montar(conSesion());
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await llenarYEnviar(false);
    expect(await screen.findByText('Debes declarar que el pasajero autorizó los avisos.')).toBeInTheDocument();
    expect(screen.getByLabelText('Nombre del supervisor')).toBeInvalid();
    expect(servidor.cuerpos).toEqual([]);
  });

  it('un error del backend en la declaración se muestra en su campo', async () => {
    const servidor = conSesion();
    servidor.errorDeCampo = { declara_autorizacion: ['Rechazada por el servidor.'] };
    montar(servidor);
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await llenarYEnviar();
    expect(await screen.findByText('Rechazada por el servidor.')).toBeInTheDocument();
  });

  it('se puede hacer otra, con el formulario vacío', async () => {
    montar(conSesion());
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await llenarYEnviar();
    await userEvent.click(await screen.findByRole('button', { name: 'Hacer otra solicitud' }));
    expect(await screen.findByLabelText('Nombre')).toHaveValue('');
  });

  it('con la sesión vencida vuelve a pedir la contraseña y lo explica', async () => {
    const servidor = conSesion();
    servidor.vencerSesion = true;
    montar(servidor);
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await llenarYEnviar();
    expect(await screen.findByText('Tu sesión venció. Ingresa de nuevo la contraseña.')).toBeInTheDocument();
    expect(screen.getByLabelText('Contraseña')).toBeInTheDocument();
  });

  it('Salir cierra la sesión', async () => {
    const { servidor } = montar(conSesion());
    await screen.findByRole('heading', { name: 'Solicitar un viaje' });
    await userEvent.click(screen.getByRole('button', { name: 'Salir' }));
    expect(await screen.findByRole('heading', { name: 'Acceso de convenio' })).toBeInTheDocument();
    expect(servidor.sesion).toBe(false);
  });
});
