/** HU-66 (CC-19): chat con el conductor en «Tu viaje» (CP-54), soporte, emergencia y lectura auditada (CP-55). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { conversacionChat, mensajeChat, ServidorChatFalso } from '../pruebas/servidorChatFalso';
import { viajeDePrueba } from '../pruebas/servidorViajesFalso';
import { VIAJE } from '../viajes/tu-viaje.test';

const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });
const CENTRAL = { telefono: '+56229990000', whatsapp: '+56999900000' };

class SocketInerte {
  onopen = null;
  onmessage = null;
  onclose = null;
  close() {}
}

function montarPasajero(ruta: string, { viaje = VIAJE, central = CENTRAL as { telefono: string | null; whatsapp: string | null } } = {}) {
  const servidor = new ServidorAuthFalso();
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const ruta = `${peticion.method} ${new URL(peticion.url).pathname}`;
    if (ruta.startsWith('GET /api/mi-cuenta/reservas/')) return json(200, viaje);
    if (ruta === 'GET /api/mi-cuenta/push/') return json(200, { clave_publica: null });
    if (ruta === 'GET /api/mi-cuenta/') return json(200, { acepta_avisos_correo: false, central });
    return original(peticion);
  };
  // Después de montar: el servidor de reservas falso de montarPanel no debe tapar las rutas del chat.
  montarPanel(ruta, { email: 'pasajero@andes.example', servidor });
  return new ServidorChatFalso(servidor);
}

const conConductor = { ...VIAJE, id: 80, estado: 'EN_CAMINO' as const, cancelable: false, conductor: { nombre: 'Juan Rojas' }, vehiculo: { marca_modelo: 'Toyota Corolla', patente: 'KTRS42' } };

beforeEach(() => {
  vi.stubGlobal('WebSocket', SocketInerte);
});

describe('HU-66 · chat con el conductor (CP-54)', () => {
  it('el pasajero escribe a su conductor mientras el viaje está en curso', async () => {
    const chat = montarPasajero('/mis-viajes/80', { viaje: conConductor });
    chat.chatDelViaje = conversacionChat({ id: 80, tipo: 'VIAJE', titulo: 'Juan Rojas', viaje: 80, no_leidos: 0, ultimo: null });
    chat.mensajes.set(80, [mensajeChat({ id: 1, conversacion: 80, texto: 'Voy en camino', autor: 'Juan Rojas' })]);
    const tarjeta = (await screen.findByRole('heading', { name: 'Chat con tu conductor' })).closest('section')!;
    expect(await within(tarjeta).findByText('Voy en camino')).toBeInTheDocument();
    await userEvent.type(within(tarjeta).getByLabelText('Mensaje para tu conductor'), 'Estoy en la puerta 3');
    await userEvent.click(within(tarjeta).getByRole('button', { name: 'Enviar' }));
    await waitFor(() => expect(chat.recibidas).toContainEqual({ ruta: 'POST /api/chat/conversaciones/80/mensajes/', cuerpo: { texto: 'Estoy en la puerta 3' } }));
    expect(within(tarjeta).getByRole('link', { name: 'Escribe a soporte sobre este viaje' })).toHaveAttribute('href', '/soporte?viaje=80');
    // Emergencia: llamar y WhatsApp de la central.
    expect(screen.getByRole('link', { name: 'Llamar a la central' })).toHaveAttribute('href', 'tel:+56229990000');
    expect(screen.getByRole('link', { name: 'WhatsApp de la central' })).toHaveAttribute('href', 'https://wa.me/56999900000');
  });

  it('al terminar el viaje queda en solo lectura', async () => {
    const chat = montarPasajero('/mis-viajes/80', { viaje: { ...conConductor, estado: 'FINALIZADO' } });
    chat.chatDelViaje = conversacionChat({ id: 80, tipo: 'VIAJE', titulo: 'Juan Rojas', viaje: 80, puede_escribir: false });
    expect(await screen.findByText('El viaje terminó: el chat queda en solo lectura.')).toBeInTheDocument();
    expect(screen.queryByLabelText('Mensaje para tu conductor')).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Llamar a la central' })).not.toBeInTheDocument();
  });

  it('sin chat (viaje sin cuenta o sin conductor) no muestra la tarjeta ni botones sin números', async () => {
    montarPasajero('/mis-viajes/80', { viaje: conConductor, central: { telefono: null, whatsapp: null } });
    await screen.findByRole('heading', { name: 'Tu viaje' });
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Chat con tu conductor' })).not.toBeInTheDocument());
    expect(screen.queryByRole('group', { name: 'Contactar a la central' })).not.toBeInTheDocument();
  });
});

describe('HU-66 · soporte', () => {
  it('escribe a la central con la referencia del viaje y aparece en el menú', async () => {
    const chat = montarPasajero('/soporte?viaje=80');
    expect(await screen.findByRole('heading', { name: 'Soporte', level: 1 })).toBeInTheDocument();
    expect(screen.getByText('Tu mensaje irá sobre el viaje N.º 80.')).toBeInTheDocument();
    await userEvent.type(await screen.findByLabelText('Mensaje para la central'), 'Olvidé mi paraguas');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    await waitFor(() => expect(chat.recibidas).toContainEqual({ ruta: 'POST /api/chat/conversaciones/90/mensajes/', cuerpo: { texto: 'Olvidé mi paraguas', viaje: 80 } }));
    expect(screen.getAllByRole('link', { name: 'Soporte' })[0]).toHaveAttribute('href', '/soporte');
  });
});

describe('HU-66 · lectura auditada de la central (CP-55)', () => {
  it('se carga solo al pedirla y avisa que queda en la auditoría', async () => {
    const contexto = montarPanel('/reservas/80');
    const chat = new ServidorChatFalso(contexto.servidor);
    contexto.viajes.agregar(viajeDePrueba({ id: 80, estado: 'EN_CAMINO' }));
    chat.mensajes.set(80, [mensajeChat({ id: 1, conversacion: 80, texto: 'Estoy en la puerta 3', autor: 'Paula Pasajera' })]);
    const boton = await screen.findByRole('button', { name: 'Ver chat con el pasajero' });
    expect(chat.lecturas).toBe(0);
    await userEvent.click(boton);
    const dialogo = await screen.findByRole('dialog', { name: 'Chat del viaje (solo lectura)' });
    expect(within(dialogo).getByText('Esta lectura quedó registrada en la auditoría.')).toBeInTheDocument();
    expect(await within(dialogo).findByText('Estoy en la puerta 3')).toBeInTheDocument();
    expect(chat.lecturas).toBe(1);
    expect(within(dialogo).queryByRole('textbox')).not.toBeInTheDocument();
  });
});
