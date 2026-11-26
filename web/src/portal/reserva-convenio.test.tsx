/** CC-23 (HU-73): reserva de convenio con correo + clave en el portal base. CP-63. */

import { fireEvent, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { jsonPortal, montarPortal } from '../pruebas/montarPortal';
import { elegirSugerencia, MAPA_CIUDAD, pines, simularSugerencias } from '../pruebas/mapa';

const PORTAL = '/solicitar/transportes-andes';
const RUTA_PASE = 'POST /api/portal/transportes-andes/convenio/pase/';
const RUTA_RESERVA = 'POST /api/portal/transportes-andes/reservas/';
// Datos sintéticos: la clave de prueba no es la de ningún convenio real.
const CLAVE = 'ABCDE-23456';
const PASE = {
  pase: 'pase-firmado-de-prueba',
  cliente_nombre: 'Minera Sintética S.A.',
  correo: 'a***@minera.example',
  vence_en: '2099-01-01T00:00:00Z',
};
const RESPUESTA = {
  id: 601,
  estado: 'PENDIENTE_CONFIRMACION',
  recogida_en: '2026-11-20T13:00:00Z',
  confirmar_hasta: '2026-11-19T13:00:00Z',
  confirma_convenio: false,
  viajes: 1,
  mensaje: 'Te enviamos un correo.',
};

afterEach(() => sessionStorage.clear());

type Responder = Parameters<typeof montarPortal>[1] extends infer O ? (O extends { responder?: infer R } ? R : never) : never;

function montar(responder?: Responder, modulo = false) {
  return montarPortal(PORTAL, {
    modulo,
    responder: (peticion, ruta) => responder?.(peticion, ruta) ?? (ruta === RUTA_PASE ? jsonPortal(200, PASE) : undefined),
  });
}

async function entrarConClave() {
  await userEvent.click(await screen.findByRole('radio', { name: 'Empresa con convenio' }));
  await userEvent.type(screen.getByLabelText('Correo de la empresa'), 'ana@minera.example');
  await userEvent.type(screen.getByLabelText('Clave del convenio'), CLAVE);
  await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
  await screen.findByText('Minera Sintética S.A.');
}

async function llenarViaje() {
  await userEvent.type(await screen.findByLabelText('Origen'), 'Av. Providencia 1208');
  await userEvent.type(screen.getByLabelText('Destino'), 'Plaza de Armas');
  await userEvent.click(screen.getByRole('button', { name: 'Siguiente: quién viaja' }));
  await screen.findByRole('heading', { name: 'Quién viaja' });
}

async function datosDeQuienPide() {
  await userEvent.type(screen.getAllByLabelText('Nombre y apellido')[0], 'Ana Solicitante');
  await userEvent.type(screen.getByLabelText('Teléfono de contacto'), '+56900009501');
  fireEvent.click(screen.getByRole('checkbox', { name: /Acepto el aviso de privacidad/ }));
}

describe('CC-23 · switch «¿Quién pide?»', () => {
  it('sin módulo aparece el switch y en modo natural no hay casilla de RUT', async () => {
    montar();
    expect(await screen.findByRole('radio', { name: 'Pasajero natural' })).toBeChecked();
    await userEvent.type(await screen.findByLabelText('Origen'), 'Av. Providencia 1208');
    await userEvent.type(screen.getByLabelText('Destino'), 'Plaza de Armas');
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    await screen.findByRole('heading', { name: 'Tus datos' });
    expect(screen.queryByRole('checkbox', { name: '¿Es una empresa?' })).not.toBeInTheDocument();
  });

  it('con el módulo de cuentas no hay switch (D2)', async () => {
    montarPortal(`${PORTAL}/reservar`, { modulo: true });
    await screen.findByLabelText('Origen');
    expect(screen.queryByRole('radio', { name: 'Empresa con convenio' })).not.toBeInTheDocument();
  });

  it('ofrece solicitar un convenio o pedir como natural', async () => {
    montar();
    await userEvent.click(await screen.findByRole('radio', { name: 'Empresa con convenio' }));
    expect(screen.getByRole('link', { name: 'Mi empresa no tiene convenio' })).toHaveAttribute('href', `${PORTAL}/convenio`);
    await userEvent.click(screen.getByRole('button', { name: 'Pedir como pasajero natural' }));
    expect(screen.getByRole('radio', { name: 'Pasajero natural' })).toBeChecked();
  });
});

describe('CC-23 · correo y clave', () => {
  it('con la clave correcta muestra la tarjeta del pase y guarda solo el pase', async () => {
    const { peticiones } = montar();
    await entrarConClave();
    expect(screen.getByText(/a\*\*\*@minera\.example/)).toBeInTheDocument();
    expect(peticiones[0]).toEqual({ ruta: RUTA_PASE, cuerpo: { correo: 'ana@minera.example', clave: CLAVE } });
    const guardado = Object.values({ ...sessionStorage }).join(' ');
    expect(guardado).toContain('pase-firmado-de-prueba');
    expect(guardado).not.toContain(CLAVE);
    // Con pase, los pasajeros salen de quién viaja: no hay contador de pasajeros en el viaje.
    expect(screen.queryByRole('group', { name: 'Pasajeros' })).not.toBeInTheDocument();
  });

  it('con una clave mala muestra el error genérico', async () => {
    montar((_p, ruta) => (ruta === RUTA_PASE ? jsonPortal(400, { detail: 'x', code: 'clave_invalida' }) : undefined));
    await userEvent.click(await screen.findByRole('radio', { name: 'Empresa con convenio' }));
    await userEvent.type(screen.getByLabelText('Correo de la empresa'), 'ana@minera.example');
    await userEvent.type(screen.getByLabelText('Clave del convenio'), 'MALA');
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByText('El correo o la clave no son válidos para un convenio vigente.')).toBeInTheDocument();
  });

  it('bloqueada tras varios intentos', async () => {
    montar((_p, ruta) => (ruta === RUTA_PASE ? jsonPortal(429, { detail: 'x', code: 'clave_bloqueada' }) : undefined));
    await userEvent.click(await screen.findByRole('radio', { name: 'Empresa con convenio' }));
    await userEvent.type(screen.getByLabelText('Correo de la empresa'), 'ana@minera.example');
    await userEvent.type(screen.getByLabelText('Clave del convenio'), CLAVE);
    await userEvent.click(screen.getByRole('button', { name: 'Continuar' }));
    expect(await screen.findByText(/Demasiados intentos con este correo/)).toBeInTheDocument();
  });
});

describe('CC-23 · quién viaja', () => {
  it('para otra persona: envía el pase y los datos del pasajero', async () => {
    const { peticiones } = montar((_p, ruta) => (ruta === RUTA_RESERVA ? jsonPortal(201, RESPUESTA) : undefined));
    await entrarConClave();
    await llenarViaje();
    await datosDeQuienPide();
    await userEvent.click(screen.getByRole('radio', { name: 'Para otra persona' }));
    const pasajero = screen.getByRole('heading', { name: 'Pasajero' }).closest('section')!;
    await userEvent.type(within(pasajero).getByLabelText('Nombre y apellido'), 'Pedro Gerente');
    await userEvent.type(within(pasajero).getByLabelText('Cargo'), 'Gerente comercial');
    await userEvent.type(within(pasajero).getByLabelText('Teléfono'), '+56900009502');
    fireEvent.click(screen.getByRole('checkbox', { name: /Declaro que informé/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByRole('heading', { name: 'Revisa tu correo' })).toBeInTheDocument();
    expect(screen.getByText('a***@minera.example')).toBeInTheDocument();
    const reserva = peticiones.find((p) => p.ruta === RUTA_RESERVA)!;
    expect(reserva.cuerpo).toMatchObject({
      pase: 'pase-firmado-de-prueba',
      para: 'OTRO',
      nombre: 'Ana Solicitante',
      pasajero_nombre: 'Pedro Gerente',
      pasajero_cargo: 'Gerente comercial',
      pasajero_telefono: '+56900009502',
      declara_informados: true,
      acompanantes: [],
      es_empresa: false,
    });
    expect(reserva.cuerpo).not.toHaveProperty('correo');
  });

  it('para otra persona sin teléfono ni declaración no envía', async () => {
    const { peticiones } = montar();
    await entrarConClave();
    await llenarViaje();
    await datosDeQuienPide();
    await userEvent.click(screen.getByRole('radio', { name: 'Para otra persona' }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(screen.getByText('Escribe el teléfono.')).toBeInTheDocument();
    expect(screen.getByText('Declara que informaste a las personas que viajan.')).toBeInTheDocument();
    expect(peticiones.filter((p) => p.ruta === RUTA_RESERVA)).toHaveLength(0);
  });

  it('mismo vehículo: teléfono opcional y el límite de la capacidad', async () => {
    montar();
    await entrarConClave();
    await llenarViaje();
    await userEvent.click(screen.getByRole('radio', { name: 'Acompañado' }));
    expect(screen.getByLabelText('Teléfono (opcional, medio de contacto)')).toBeInTheDocument();
    // La capacidad de la flota de prueba es 6: hasta 5 acompañantes en el mismo vehículo.
    const agregar = screen.getByRole('button', { name: 'Agregar un acompañante' });
    for (let i = 0; i < 4; i += 1) await userEvent.click(agregar);
    expect(screen.getAllByRole('heading', { name: /^Acompañante \d$/ })).toHaveLength(5);
    expect(agregar).toBeDisabled();
  });

  it('vehículos separados: el teléfono es obligatorio por persona y avisa cuántos viajes creó', async () => {
    const { peticiones } = montar((_p, ruta) => (ruta === RUTA_RESERVA ? jsonPortal(201, { ...RESPUESTA, viajes: 2 }) : undefined));
    await entrarConClave();
    await llenarViaje();
    await datosDeQuienPide();
    await userEvent.click(screen.getByRole('radio', { name: 'Acompañado' }));
    await userEvent.click(screen.getByRole('radio', { name: 'Vehículos separados' }));
    const acompanante = screen.getByRole('heading', { name: 'Acompañante 1' }).closest('section')!;
    await userEvent.type(within(acompanante).getByLabelText('Nombre y apellido'), 'Laura Díaz');
    await userEvent.type(within(acompanante).getByLabelText('Cargo'), 'Analista');
    fireEvent.click(screen.getByRole('checkbox', { name: /Declaro que informé/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(within(acompanante).getByText('Escribe el teléfono.')).toBeInTheDocument();
    await userEvent.type(within(acompanante).getByLabelText('Teléfono'), '+56900009601');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByText(/2 traslados/)).toBeInTheDocument();
    expect(peticiones.find((p) => p.ruta === RUTA_RESERVA)!.cuerpo).toMatchObject({
      vehiculos: 'SEPARADOS',
      acompanantes: [{ nombre: 'Laura Díaz', cargo: 'Analista', telefono: '+56900009601', correo: '' }],
    });
  });

  it('con el pase vencido vuelve al paso de la clave', async () => {
    montar((_p, ruta) =>
      ruta === RUTA_RESERVA ? jsonPortal(401, { detail: 'Tu acceso de convenio venció. Ingresa de nuevo tu correo y la clave.', code: 'pase_vencido' }) : undefined,
    );
    await entrarConClave();
    await llenarViaje();
    await datosDeQuienPide();
    await userEvent.click(screen.getByRole('button', { name: 'Enviar solicitud' }));
    expect(await screen.findByText(/Tu acceso de convenio venció/)).toBeInTheDocument();
    expect(screen.getByLabelText('Clave del convenio')).toBeInTheDocument();
    expect(sessionStorage.length).toBe(0);
  });
});

describe('HU-71 · mapa en la reserva de convenio sin cuenta', () => {
  it('con el pase, el punto elegido se ve bajo las direcciones', async () => {
    simularSugerencias();
    montar();
    await entrarConClave();
    await elegirSugerencia(await screen.findByRole('combobox', { name: 'Origen' }), 0);
    expect(pines(MAPA_CIUDAD)).toEqual(['Punto de recogida']);
    vi.unstubAllGlobals();
  });
});
