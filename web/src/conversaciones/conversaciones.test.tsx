/** HU-30 con HU-67 (CC-19): historial de WhatsApp en solo lectura («canal retirado»). */

import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { conversacionDePrueba, ServidorConversacionesFalso } from '../pruebas/servidorConversacionesFalso';

function montar(ruta: string, conversaciones = [conversacionDePrueba()]) {
  const contexto = montarPanel(ruta);
  const chat = new ServidorConversacionesFalso(contexto.servidor);
  chat.conversaciones = conversaciones;
  return { ...contexto, chat };
}

describe('historial de WhatsApp', () => {
  it('muestra el pasajero, el último mensaje y la reserva, con el aviso del canal retirado', async () => {
    montar('/conversaciones');
    expect(await screen.findByRole('heading', { name: 'Historial WhatsApp (canal retirado)', level: 1 })).toBeInTheDocument();
    expect(screen.getByText(/El canal de WhatsApp se retiró: este historial es de solo lectura/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Ir al Chat' })).toHaveAttribute('href', '/chat');
    const enlace = await screen.findByRole('link', { name: 'Ana Pérez' });
    expect(enlace).toHaveAttribute('href', '/conversaciones/5');
    const fila = enlace.closest('tr')!;
    expect(within(fila).getByText('¿Viene pronto?')).toBeInTheDocument();
    expect(within(fila).getByRole('link', { name: '#8 · En camino' })).toHaveAttribute('href', '/reservas/8');
  });

  it('distingue lo último de la central y sin reserva', async () => {
    montar('/conversaciones', [conversacionDePrueba({ ultima_direccion: 'SALIENTE', ultimo_mensaje: 'Ya vamos', reserva: null })]);
    expect(await screen.findByText('Central: Ya vamos')).toBeInTheDocument();
    expect(screen.getByText('Sin reserva')).toBeInTheDocument();
  });

  it('sin mensajes lo dice', async () => {
    montar('/conversaciones', []);
    expect(await screen.findByText('No hay mensajes de WhatsApp en el historial.')).toBeInTheDocument();
  });

  it('una falla ofrece reintentar', async () => {
    const { chat } = montar('/conversaciones');
    chat.siguiente('GET /api/conversaciones/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('link', { name: 'Ana Pérez' })).toBeInTheDocument();
  });

  it('aparece en el menú como «Historial WhatsApp»', async () => {
    montar('/');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Historial WhatsApp' })).toBeInTheDocument();
  });
});

describe('hilo del historial', () => {
  it('muestra los mensajes con autor y estado, sin campo para responder (CP-57)', async () => {
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
    expect(screen.getByRole('link', { name: '#8 · En camino' })).toBeInTheDocument();
    expect(screen.getByText(/Historial de WhatsApp en solo lectura/)).toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Enviar' })).not.toBeInTheDocument();
  });

  it('otra empresa o inexistente: no encontrado', async () => {
    montar('/conversaciones/99');
    expect(await screen.findByRole('heading', { name: 'No encontrado' })).toBeInTheDocument();
  });

  it('una falla de carga ofrece reintentar', async () => {
    const { chat } = montar('/conversaciones/5');
    chat.siguiente('GET /api/conversaciones/5/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('list', { name: 'Mensajes' })).toBeInTheDocument();
  });
});
