/** HU-30: chat de WhatsApp desde el panel (CP-27). */

import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { conversacionDePrueba, ServidorConversacionesFalso } from '../pruebas/servidorConversacionesFalso';

const AVISO = 'Fuera de la ventana de 24 h: solo plantillas aprobadas (pendiente PR-11)';

function montar(ruta: string, conversaciones = [conversacionDePrueba()]) {
  const contexto = montarPanel(ruta);
  const chat = new ServidorConversacionesFalso(contexto.servidor);
  chat.conversaciones = conversaciones;
  return { ...contexto, chat };
}

describe('bandeja', () => {
  it('muestra el pasajero, el último mensaje y la reserva vinculada', async () => {
    montar('/conversaciones');
    const enlace = await screen.findByRole('link', { name: 'Ana Pérez' });
    expect(enlace).toHaveAttribute('href', '/conversaciones/5');
    const fila = enlace.closest('tr')!;
    expect(within(fila).getByText('¿Viene pronto?')).toBeInTheDocument();
    expect(within(fila).getByRole('link', { name: '#8 · En camino' })).toHaveAttribute('href', '/reservas/8');
    expect(within(fila).getByText('Abierta')).toBeInTheDocument();
  });

  it('distingue lo último enviado, sin reserva y con la ventana cerrada', async () => {
    montar('/conversaciones', [conversacionDePrueba({ ultima_direccion: 'SALIENTE', ultimo_mensaje: 'Ya vamos', reserva: null, dentro_ventana: false })]);
    expect(await screen.findByText('Tú: Ya vamos')).toBeInTheDocument();
    expect(screen.getByText('Sin reserva')).toBeInTheDocument();
    expect(screen.getByText('Cerrada')).toBeInTheDocument();
  });

  it('sin conversaciones lo dice', async () => {
    montar('/conversaciones', []);
    expect(await screen.findByText('Aún no hay conversaciones de WhatsApp.')).toBeInTheDocument();
  });

  it('una falla ofrece reintentar', async () => {
    const { chat } = montar('/conversaciones');
    chat.siguiente('GET /api/conversaciones/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('link', { name: 'Ana Pérez' })).toBeInTheDocument();
  });

  it('aparece en el menú del despachador', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Conversaciones' })).toBeInTheDocument();
  });
});

describe('hilo', () => {
  it('muestra los mensajes con autor y estado', async () => {
    const base = conversacionDePrueba();
    montar('/conversaciones/5', [
      {
        ...base,
        mensajes: [
          ...base.mensajes,
          { id: 2, direccion: 'SALIENTE', tipo: 'SESION', cuerpo: 'Ya vamos', estado_entrega: 'READ', usuario: 'Diego Despacho', viaje: 8, creado_en: '2026-07-15T12:01:00Z' },
          { id: 3, direccion: 'SALIENTE', tipo: 'SESION', cuerpo: 'Otro', estado_entrega: 'FAILED', usuario: 'Diego Despacho', viaje: 8, creado_en: '2026-07-15T12:02:00Z' },
        ],
      },
    ]);
    const hilo = await screen.findByRole('list', { name: 'Mensajes' });
    const items = within(hilo).getAllByRole('listitem');
    expect(items.map((i) => within(i).getByText(/./, { selector: 'p' }).textContent)).toEqual(['¿Viene pronto?', 'Ya vamos', 'Otro']);
    expect(items[1]).toHaveTextContent('Diego Despacho · Leído');
    expect(items[2]).toHaveTextContent('No se pudo enviar');
    expect(items[0]).not.toHaveTextContent('Entregado');
    expect(screen.getByRole('link', { name: '#8 · En camino' })).toBeInTheDocument();
  });

  it('dentro de la ventana envía texto libre, sin espacios sobrantes, y limpia el campo', async () => {
    const { chat } = montar('/conversaciones/5');
    const campo = await screen.findByRole('textbox', { name: 'Respuesta' });
    expect(campo).toBeEnabled();
    expect(screen.queryByText(AVISO)).not.toBeInTheDocument();
    await userEvent.type(campo, '  Vamos en camino  ');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    await waitFor(() => expect(chat.cuerpos).toEqual([{ texto: 'Vamos en camino' }]));
    await waitFor(() => expect(campo).toHaveValue(''));
    expect(await screen.findByText('Vamos en camino')).toBeInTheDocument();
  });

  it('sin texto no se puede enviar', async () => {
    montar('/conversaciones/5');
    await screen.findByRole('textbox', { name: 'Respuesta' });
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled();
  });

  it('fuera de la ventana deshabilita el campo con el aviso', async () => {
    const { chat } = montar('/conversaciones/5', [conversacionDePrueba({ dentro_ventana: false })]);
    expect(await screen.findByText(AVISO)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Respuesta' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Enviar' })).toBeDisabled();
    expect(chat.cuerpos).toEqual([]);
  });

  it('si la ventana se cierra al enviar, muestra el aviso y conserva el texto', async () => {
    const { chat } = montar('/conversaciones/5');
    chat.siguiente('POST /api/conversaciones/5/mensajes/', { estado: 409, cuerpo: { detail: 'Fuera.', code: 'fuera_de_ventana' } });
    const campo = await screen.findByRole('textbox', { name: 'Respuesta' });
    await userEvent.type(campo, 'Hola');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    expect(await screen.findByText(AVISO)).toBeInTheDocument();
    expect(campo).toBeDisabled();
    expect(campo).toHaveValue('Hola');
  });

  it('otra falla se informa y conserva el texto', async () => {
    const { chat } = montar('/conversaciones/5');
    chat.siguiente('POST /api/conversaciones/5/mensajes/', { estado: 500, cuerpo: {} });
    const campo = await screen.findByRole('textbox', { name: 'Respuesta' });
    await userEvent.type(campo, 'Hola');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(campo).toHaveValue('Hola');
    expect(campo).toBeEnabled();
  });

  it('otra empresa o inexistente: no encontrada', async () => {
    montar('/conversaciones/99');
    expect(await screen.findByRole('heading', { name: 'No encontrado' })).toBeInTheDocument();
  });

  it('una falla de carga ofrece reintentar', async () => {
    const { chat } = montar('/conversaciones/5');
    chat.siguiente('GET /api/conversaciones/5/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('textbox', { name: 'Respuesta' })).toBeInTheDocument();
  });
});
