// @vitest-environment jsdom
/** HU-61 y HU-62 (CC-19): chat de la app del conductor y su canal en vivo. */

import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CanalChat, type EventoChat, type MensajeChat } from '../chat/canal';
import type { SocketMinimo } from '../conductor/canal';
import { ErrorApi, SinRed } from '../sesion/sesion';
import { Chat, type Pedir } from './Chat';

afterEach(cleanup);

const central = { id: 1, tipo: 'CENTRAL' as const, titulo: 'Central', no_leidos: 1, ultimo: { texto: 'Te espera', autor: 'Central', creado_en: '2026-11-17T12:00:00Z' } };

function mensaje(cambios: Partial<MensajeChat> = {}): MensajeChat {
  return { id: 1, conversacion: 1, texto: 'Te espera el pasajero', rapida: '', autor: 'Central', propio: false, creado_en: '2026-11-17T12:00:00Z', ...cambios };
}

function servidor(mensajes: MensajeChat[] = [mensaje()]) {
  const llamadas: { metodo: string; ruta: string; cuerpo?: unknown }[] = [];
  let leido = 0;
  const pedir = vi.fn(async (metodo: string, ruta: string, cuerpo?: unknown) => {
    llamadas.push({ metodo, ruta, cuerpo });
    if (ruta === '/api/chat/conversaciones/') return [central];
    if (ruta === '/api/chat/personal/') return [{ id: 2, nombre: 'Ana Rojas' }];
    if (ruta === '/api/chat/directos/') return { id: 9, tipo: 'DIRECTO', titulo: 'Ana Rojas', no_leidos: 0, ultimo: null };
    if (ruta === '/api/chat/grupos/') return { id: 10, nombre: (cuerpo as { nombre: string }).nombre };
    if (ruta.endsWith('/leido/')) return null;
    if (metodo === 'POST' && ruta.endsWith('/mensajes/')) {
      const { texto, rapida } = cuerpo as { texto?: string; rapida?: string };
      mensajes.push(mensaje({ id: 100 + mensajes.length, texto: texto ?? (rapida === 'LLEGUE' ? 'Llegué' : rapida!), autor: 'Carla', propio: true }));
      leido = 100 + mensajes.length - 1;
      return mensajes.at(-1);
    }
    if (ruta.includes('?antes=')) return { results: [mensaje({ id: 0, texto: 'Anterior' })], hay_mas: false, leido_por_otros_hasta: leido };
    if (ruta.endsWith('/mensajes/')) return { results: [...mensajes], hay_mas: true, leido_por_otros_hasta: leido };
    throw new Error(`ruta inesperada ${ruta}`);
  });
  return { pedir: pedir as unknown as Pedir, llamadas, pedirFalso: pedir };
}

function canalFalso() {
  const oyentes = new Set<(evento: EventoChat) => void>();
  return {
    alEvento: (oyente: (evento: EventoChat) => void) => (oyentes.add(oyente), () => oyentes.delete(oyente)),
    emitir: (evento: EventoChat) => act(() => oyentes.forEach((o) => o(evento))),
  };
}

describe('chat de la app', () => {
  it('lista la Central con no leídos, abre el hilo y marca leído', async () => {
    const { pedir, llamadas } = servidor();
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje={false} volver={() => {}} />);
    const boton = await screen.findByRole('button', { name: /Central/ });
    expect(boton.textContent).toContain('Central: Te espera');
    expect(boton.textContent).toContain('1 sin leer');
    expect(screen.queryByText(/Evita escribir mientras manejas/)).toBeNull();
    fireEvent.click(boton);
    expect(await screen.findByText('Te espera el pasajero')).toBeTruthy();
    await waitFor(() => expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/conversaciones/1/leido/', cuerpo: { hasta: 1 } }));
  });

  it('con viaje en curso avisa sin bloquear y las respuestas rápidas se envían', async () => {
    const { pedir, llamadas } = servidor();
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje volver={() => {}} />);
    expect(screen.getByRole('status').textContent).toContain('Evita escribir mientras manejas');
    fireEvent.click(await screen.findByRole('button', { name: /Central/ }));
    const grupo = await screen.findByRole('group', { name: 'Respuestas rápidas' });
    expect(grupo.querySelectorAll('button')).toHaveLength(5);
    fireEvent.click(screen.getByRole('button', { name: 'Llegué' }));
    await waitFor(() => expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/conversaciones/1/mensajes/', cuerpo: { rapida: 'LLEGUE' } }));
    expect((await screen.findByText('Llegué', { selector: 'p' })).parentElement?.textContent).toContain('Leído');
  });

  it('escribe texto libre, carga anteriores y recarga con el canal', async () => {
    const { pedir, llamadas } = servidor();
    const canal = canalFalso();
    render(<Chat pedir={pedir} canal={canal} enViaje={false} volver={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: /Central/ }));
    const area = (await screen.findByLabelText('Mensaje')) as HTMLTextAreaElement;
    fireEvent.change(area, { target: { value: '  Voy saliendo ' } });
    expect(screen.getByText('15/1000')).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    await waitFor(() => expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/conversaciones/1/mensajes/', cuerpo: { texto: 'Voy saliendo' } }));
    await waitFor(() => expect(area.value).toBe(''));
    fireEvent.click(screen.getByRole('button', { name: 'Ver mensajes anteriores' }));
    expect(await screen.findByText('Anterior')).toBeTruthy();
    const antes = llamadas.length;
    canal.emitir({ tipo: 'mensaje', mensaje: mensaje({ id: 50 }) });
    await waitFor(() => expect(llamadas.length).toBeGreaterThan(antes));
    canal.emitir({ tipo: 'mensaje', mensaje: mensaje({ id: 51, conversacion: 7 }) });
  });

  it('agrega mensajes en tiempo real sin duplicar, marca leído y hace scroll al final', async () => {
    const scroll = vi.fn();
    HTMLElement.prototype.scrollIntoView = scroll;
    const { pedir, llamadas } = servidor();
    const canal = canalFalso();
    render(<Chat pedir={pedir} canal={canal} enViaje={false} volver={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: /Central/ }));
    expect(await screen.findByText('Te espera el pasajero')).toBeTruthy();
    await waitFor(() => expect(scroll).toHaveBeenCalledTimes(1));

    const entrante = mensaje({ id: 50, texto: 'Pasajero en puerta 4' });
    canal.emitir({ tipo: 'mensaje', mensaje: entrante });
    canal.emitir({ tipo: 'mensaje', mensaje: entrante });
    expect(await screen.findAllByText('Pasajero en puerta 4')).toHaveLength(1);
    await waitFor(() => expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/conversaciones/1/leido/', cuerpo: { hasta: 50 } }));
    await waitFor(() => expect(scroll).toHaveBeenCalledTimes(2));

    // Cargar mensajes anteriores no fuerza scroll al final.
    fireEvent.click(screen.getByRole('button', { name: 'Ver mensajes anteriores' }));
    expect(await screen.findByText('Anterior')).toBeTruthy();
    expect(scroll.mock.calls.length).toBe(2);
  });

  it('muestra los errores del servidor y de la red', async () => {
    const { pedir, pedirFalso } = servidor();
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje={false} volver={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: /Central/ }));
    await screen.findByText('Te espera el pasajero');
    pedirFalso.mockRejectedValueOnce(new ErrorApi(429, null));
    fireEvent.click(screen.getByRole('button', { name: 'Necesito ayuda' }));
    expect(await screen.findByText('Estás enviando muchos mensajes seguidos. Espera un momento.')).toBeTruthy();
    pedirFalso.mockRejectedValueOnce(new SinRed());
    fireEvent.click(screen.getByRole('button', { name: 'Llegué' }));
    expect(await screen.findByText('Sin conexión con el servidor. Intenta de nuevo.')).toBeTruthy();
  });

  it('la lista se reintenta si falla', async () => {
    const { pedir, pedirFalso } = servidor();
    pedirFalso.mockRejectedValueOnce(new ErrorApi(500, { detail: 'Error del servidor' }));
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje={false} volver={() => {}} />);
    expect(await screen.findByText(/Error del servidor/)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByRole('button', { name: /Central/ })).toBeTruthy();
  });

  it('abre un directo y crea un grupo', async () => {
    const { pedir, llamadas } = servidor([]);
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje={false} volver={() => {}} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo directo' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Escribir a Ana Rojas' }));
    expect(await screen.findByRole('heading', { name: 'Ana Rojas' })).toBeTruthy();
    expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/directos/', cuerpo: { usuario: 2 } });
    fireEvent.click(screen.getByRole('button', { name: 'Volver a las conversaciones' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Nuevo grupo' }));
    fireEvent.click(await screen.findByRole('button', { name: 'Crear grupo' }));
    expect(screen.getByText('Ponle un nombre al grupo y elige al menos a una persona.')).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Nombre del grupo'), { target: { value: 'Aeropuerto' } });
    fireEvent.click(screen.getByLabelText('Ana Rojas'));
    fireEvent.click(screen.getByRole('button', { name: 'Crear grupo' }));
    expect(await screen.findByRole('heading', { name: 'Aeropuerto' })).toBeTruthy();
    expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/grupos/', cuerpo: { nombre: 'Aeropuerto', ids_integrantes: [2] } });
  });
});

describe('chat con el pasajero (HU-66)', () => {
  it('con viaje en curso abre el chat del pasajero; terminado, solo lectura', async () => {
    const { pedir, pedirFalso, llamadas } = servidor([]);
    const delViaje = { id: 80, tipo: 'VIAJE' as const, titulo: 'Paula Pasajera', no_leidos: 0, ultimo: null, puede_escribir: true };
    pedirFalso.mockImplementationOnce(async () => [central]);
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje viajeId={8} volver={() => {}} />);
    pedirFalso.mockImplementationOnce(async (metodo: string, ruta: string) => (llamadas.push({ metodo, ruta }), delViaje));
    fireEvent.click(await screen.findByRole('button', { name: 'Chat con el pasajero' }));
    expect(await screen.findByRole('heading', { name: 'Paula Pasajera' })).toBeTruthy();
    expect(llamadas).toContainEqual({ metodo: 'POST', ruta: '/api/chat/viajes/8/' });
    expect(screen.getByLabelText('Mensaje')).toBeTruthy();
    cleanup();
    pedirFalso.mockImplementationOnce(async () => [{ ...delViaje, puede_escribir: false }] as never);
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje={false} volver={() => {}} />);
    expect(screen.queryByRole('button', { name: 'Chat con el pasajero' })).toBeNull();
    fireEvent.click(await screen.findByRole('button', { name: /Paula Pasajera/ }));
    expect(await screen.findByText('El viaje terminó: este chat queda en solo lectura.')).toBeTruthy();
    expect(screen.queryByLabelText('Mensaje')).toBeNull();
  });

  it('sin cuenta del pasajero lo dice', async () => {
    const { pedir, pedirFalso } = servidor([]);
    render(<Chat pedir={pedir} canal={canalFalso()} enViaje viajeId={8} volver={() => {}} />);
    await screen.findByRole('button', { name: /Central/ });
    pedirFalso.mockRejectedValueOnce(new ErrorApi(404, { detail: 'El pasajero no tiene cuenta: comunícate por la central.' }));
    fireEvent.click(screen.getByRole('button', { name: 'Chat con el pasajero' }));
    expect(await screen.findByText(/El pasajero no tiene cuenta/)).toBeTruthy();
  });
});

describe('canal del chat', () => {
  function crear() {
    const sockets: (SocketMinimo & { url: string; protocolos: string[]; close: ReturnType<typeof vi.fn> })[] = [];
    const sesion = { access: 'A1', renovar: vi.fn(async () => 'A2') };
    const canal = new CanalChat('ws://x.example/ws/chat/', sesion, (url, protocolos) => {
      const socket = { url, protocolos, onopen: null, onmessage: null, onclose: null, close: vi.fn() };
      sockets.push(socket);
      return socket;
    });
    return { canal, sockets, sesion };
  }

  it('entrega los eventos, ignora el pong, renueva con 4401 y se reconecta', async () => {
    vi.useFakeTimers();
    const { canal, sockets, sesion } = crear();
    const recibidos: EventoChat[] = [];
    canal.alEvento((e) => recibidos.push(e));
    canal.iniciar();
    await vi.advanceTimersByTimeAsync(0);
    expect(sockets[0].protocolos).toEqual(['flotaagil', 'A1']);
    sockets[0].onopen?.();
    sockets[0].onmessage?.({ data: JSON.stringify({ tipo: 'pong' }) });
    sockets[0].onmessage?.({ data: JSON.stringify({ tipo: 'conversaciones' }) });
    expect(recibidos).toEqual([{ tipo: 'conversaciones' }]);
    sockets[0].onclose?.({ code: 4401 });
    await vi.advanceTimersByTimeAsync(0);
    expect(sesion.renovar).toHaveBeenCalled();
    expect(sockets[1].protocolos).toEqual(['flotaagil', 'A2']);
    sockets[1].onclose?.({ code: 1006 });
    await vi.advanceTimersByTimeAsync(1000);
    expect(sockets).toHaveLength(3);
    canal.detener();
    expect(sockets[2].close).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
