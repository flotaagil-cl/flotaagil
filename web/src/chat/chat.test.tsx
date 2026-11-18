/** HU-61 y HU-62 (CC-19): chat de trabajo del panel. */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { conversacionChat, mensajeChat, ServidorChatFalso } from '../pruebas/servidorChatFalso';

class SocketFalso {
  static creados: SocketFalso[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: ((evento: { code: number }) => void) | null = null;
  constructor(
    readonly url: string,
    readonly protocolos: string[],
  ) {
    SocketFalso.creados.push(this);
  }
  close() {}
}

function montar(ruta: string, email?: string) {
  const contexto = montarPanel(ruta, email ? { email } : undefined);
  const chat = new ServidorChatFalso(contexto.servidor);
  return { ...contexto, chat };
}

const pedidas = (urls: string[], ruta: string) => urls.filter((u) => u === ruta).length;

beforeEach(() => {
  SocketFalso.creados = [];
  vi.stubGlobal('WebSocket', SocketFalso);
});

describe('bandeja', () => {
  it('aparece en el menú y muestra los no leídos del hilo central', async () => {
    montar('/chat');
    const menu = await screen.findByRole('navigation', { name: 'Menú principal' });
    expect(within(menu).getByRole('link', { name: 'Chat' })).toHaveAttribute('href', '/chat');
    const enlace = await screen.findByRole('link', { name: /Pedro Soto/ });
    expect(enlace).toHaveAttribute('href', '/chat/1');
    expect(enlace).toHaveTextContent('Conductor · Pedro Soto: Voy en camino');
    expect(within(enlace).getByText('1 sin leer')).toBeInTheDocument();
    expect(screen.getByText('Elige una conversación o empieza una nueva.')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Moderación de grupos' })).not.toBeInTheDocument();
  });

  it('un evento del canal en vivo vuelve a pedir la bandeja', async () => {
    const { servidor } = montar('/chat');
    await screen.findByRole('link', { name: /Pedro Soto/ });
    const canal = SocketFalso.creados.find((s) => s.url.endsWith('/ws/chat/'))!;
    expect(canal.protocolos[0]).toBe('flotaagil');
    const antes = pedidas(servidor.urls, 'GET /api/chat/conversaciones/');
    act(() => canal.onmessage!({ data: JSON.stringify({ tipo: 'mensaje', mensaje: mensajeChat({ id: 2 }) }) }));
    await waitFor(() => expect(pedidas(servidor.urls, 'GET /api/chat/conversaciones/')).toBeGreaterThan(antes));
  });

  it('sin conversaciones lo dice', async () => {
    const { chat } = montar('/chat');
    chat.conversaciones = [];
    expect(await screen.findByText('Aún no hay conversaciones.')).toBeInTheDocument();
  });
});

describe('hilo', () => {
  it('muestra el autor, marca leído y envía con el estado de lectura', async () => {
    const { chat } = montar('/chat/1');
    expect(await screen.findByText('Voy en camino', { selector: 'p' })).toBeInTheDocument();
    expect(screen.getByText(/conductor ve los mensajes del equipo como «Central»/)).toBeInTheDocument();
    await waitFor(() => expect(chat.recibidas).toContainEqual({ ruta: 'POST /api/chat/conversaciones/1/leido/', cuerpo: { hasta: 1 } }));
    const area = screen.getByLabelText('Mensaje');
    await userEvent.type(area, '  Ok, avisamos al pasajero ');
    expect(screen.getByText('27/1000')).toBeInTheDocument();
    chat.leidoPorOtros = 5000;
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    expect(chat.recibidas).toContainEqual({ ruta: 'POST /api/chat/conversaciones/1/mensajes/', cuerpo: { texto: 'Ok, avisamos al pasajero' } });
    const enviado = await screen.findByText('Ok, avisamos al pasajero');
    expect(enviado.parentElement).toHaveTextContent('Leído');
    expect(area).toHaveValue('');
  });

  it('el antispam y los errores conservan el texto', async () => {
    const { chat } = montar('/chat/1');
    chat.siguiente('POST /api/chat/conversaciones/1/mensajes/', { estado: 429, cuerpo: { detail: 'Throttled' } });
    await userEvent.type(await screen.findByLabelText('Mensaje'), 'Hola');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar' }));
    expect(await screen.findByText('Estás enviando muchos mensajes seguidos. Espera un momento.')).toBeInTheDocument();
    expect(screen.getByLabelText('Mensaje')).toHaveValue('Hola');
  });

  it('carga los mensajes anteriores por páginas', async () => {
    const { chat } = montar('/chat/1');
    chat.mensajes.set(
      1,
      Array.from({ length: 35 }, (_, i) => mensajeChat({ id: i + 1, texto: `m${i + 1}`, rapida: '' })),
    );
    expect(await screen.findByText('m35')).toBeInTheDocument();
    expect(screen.queryByText('m5')).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Ver mensajes anteriores' }));
    expect(await screen.findByText('m5')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Ver mensajes anteriores' })).not.toBeInTheDocument();
  });

  it('una conversación ajena o inexistente lo dice', async () => {
    montar('/chat/77');
    expect(await screen.findByText('Esa conversación no existe o ya no participas en ella.')).toBeInTheDocument();
  });
});

describe('directos y grupos', () => {
  it('abre un directo con alguien del personal', async () => {
    const { chat, router } = montar('/chat');
    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo directo' }));
    await userEvent.click(await screen.findByRole('button', { name: 'Escribir a Carla Conductora' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/chat/50'));
    expect(chat.recibidas).toContainEqual({ ruta: 'POST /api/chat/directos/', cuerpo: { usuario: 3 } });
    expect(await screen.findByRole('heading', { name: 'Carla Conductora', level: 2 })).toBeInTheDocument();
  });

  it('crea un grupo y lo gestiona', async () => {
    const { chat, router } = montar('/chat');
    await userEvent.click(await screen.findByRole('button', { name: 'Nuevo grupo' }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear grupo' }));
    expect(screen.getByText('Ponle un nombre al grupo y elige al menos a una persona.')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Nombre del grupo'), 'Turno noche');
    await userEvent.click(await screen.findByLabelText('Carla Conductora'));
    await userEvent.click(screen.getByRole('button', { name: 'Crear grupo' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/chat/60'));
    expect(chat.recibidas).toContainEqual({ ruta: 'POST /api/chat/grupos/', cuerpo: { nombre: 'Turno noche', ids_integrantes: [3] } });
    chat.grupos.set(60, {
      ...chat.grupos.get(60)!,
      integrantes: [
        { id: 2, nombre: 'Diego Despacho', rol: 'DESPACHADOR' },
        { id: 3, nombre: 'Carla Conductora', rol: 'CONDUCTOR' },
      ],
    });
    await userEvent.click(await screen.findByRole('button', { name: 'Gestionar grupo' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Gestionar grupo' });
    const nombre = await within(dialogo).findByLabelText('Nombre del grupo');
    await userEvent.clear(nombre);
    await userEvent.type(nombre, 'Noche SCL');
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Guardar nombre' }));
    await waitFor(() => expect(chat.recibidas).toContainEqual({ ruta: 'PATCH /api/chat/grupos/60/', cuerpo: { nombre: 'Noche SCL' } }));
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Quitar a Carla Conductora' }));
    await waitFor(() => expect(chat.recibidas.map((r) => r.ruta)).toContain('DELETE /api/chat/grupos/60/integrantes/3/'));
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Borrar grupo' }));
    await userEvent.click(within(dialogo).getByRole('button', { name: 'Confirmar: borrar el grupo' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/chat'));
    expect(chat.recibidas.map((r) => r.ruta)).toContain('DELETE /api/chat/grupos/60/');
  });

  it('muestra el error del backend al gestionar', async () => {
    const { chat } = montar('/chat/60');
    chat.grupos.set(60, { id: 60, nombre: 'Día', integrantes: [{ id: 3, nombre: 'Carla Conductora', rol: 'CONDUCTOR' }], creado_por: 'Carla Conductora', creado_en: '2026-11-17T12:00:00Z', ultimo_mensaje_en: null });
    chat.conversaciones = [conversacionChat({ id: 60, tipo: 'GRUPO', titulo: 'Día', puede_gestionar: true })];
    chat.mensajes.set(60, []);
    chat.siguiente('DELETE /api/chat/grupos/60/integrantes/3/', { estado: 403, cuerpo: { detail: 'Solo quien creó el grupo o el administrador quitan integrantes.', code: 'no_es_creador' } });
    await userEvent.click(await screen.findByRole('button', { name: 'Gestionar grupo' }));
    expect(screen.queryByRole('button', { name: 'Borrar grupo' })).not.toBeInTheDocument();
    await userEvent.click(await screen.findByRole('button', { name: 'Quitar a Carla Conductora' }));
    expect(await screen.findByText('Solo quien creó el grupo o el administrador quitan integrantes.')).toBeInTheDocument();
  });
});

describe('moderación (CP-53)', () => {
  it('el administrador ve solo los metadatos de los grupos', async () => {
    const { chat } = montar('/chat', 'admin@andes.example');
    chat.grupos.set(9, { id: 9, nombre: 'Turno noche', integrantes: [{ id: 3, nombre: 'Carla Conductora', rol: 'CONDUCTOR' }], creado_por: 'Carla Conductora', creado_en: '2026-11-17T12:00:00Z', ultimo_mensaje_en: null });
    await userEvent.click(await screen.findByRole('link', { name: 'Moderación de grupos' }));
    const fila = (await screen.findByRole('cell', { name: 'Turno noche' })).closest('tr')!;
    expect(fila).toHaveTextContent('Carla Conductora');
    expect(fila).toHaveTextContent('Sin mensajes');
    expect(screen.getByText(/no ves los mensajes de los grupos ni de los directos/)).toBeInTheDocument();
    await userEvent.click(within(fila).getByRole('button', { name: 'Gestionar Turno noche' }));
    const dialogo = await screen.findByRole('dialog', { name: 'Gestionar grupo' });
    expect(within(dialogo).queryByRole('button', { name: 'Agregar' })).not.toBeInTheDocument();
    expect(within(dialogo).getByRole('button', { name: 'Borrar grupo' })).toBeInTheDocument();
  });
});
