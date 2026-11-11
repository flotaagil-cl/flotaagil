/** HU-35: cuenta opcional del pasajero en la web. */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createMemoryRouter } from 'react-router';
import { describe, expect, it } from 'vitest';
import { App } from '../App';
import { crearEntorno, crearLocks } from '../pruebas/entornoFalso';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { EMPRESA_PORTAL, ServidorPortalFalso } from '../pruebas/servidorPortalFalso';
import { crearRutas } from '../rutas/tabla';

const CUENTA = {
  nombre: 'Pablo Pasajero',
  email: 'pasajero@andes.example',
  telefono: '+56987654321',
  empresa: 'Transportes Andes Demo SpA',
  empresa_slug: 'transportes-andes',
};

function reserva(id: number, estado: string, cancelable: boolean) {
  return {
    id,
    estado,
    estado_texto: estado === 'SOLICITADO' ? 'Solicitado' : 'En camino',
    canal: 'WEB',
    origen_dir: `Origen ${id}`,
    destino_dir: 'Destino',
    recogida_en: '2026-10-30T17:00:00Z',
    cancelable,
    historial: [{ estado_anterior: null, estado_nuevo: estado, actor: 'PASAJERO', usuario: null, manual: false, distancia_m: null, contingencia: false, creado_en: '2026-10-30T15:00:00Z' }],
  };
}

function instalar(auth: ServidorAuthFalso) {
  const anterior = auth.api;
  const llamadas: string[] = [];
  let reservas = [reserva(1, 'SOLICITADO', true), reserva(2, 'EN_CAMINO', false)];
  auth.api = async (peticion: Request, url: URL): Promise<Respuesta> => {
    const ruta = `${peticion.method} ${url.pathname}`;
    llamadas.push(ruta);
    if (ruta === 'GET /api/mi-cuenta/') return { estado: 200, cuerpo: CUENTA };
    if (ruta === 'DELETE /api/mi-cuenta/') return { estado: 204, cuerpo: undefined };
    if (ruta === 'GET /api/mi-cuenta/reservas/') return { estado: 200, cuerpo: { count: reservas.length, next: null, previous: null, results: reservas } };
    if (ruta === 'POST /api/mi-cuenta/reservas/1/cancelar/') {
      reservas = reservas.map((r) => (r.id === 1 ? { ...r, estado: 'CANCELADO', estado_texto: 'Cancelado', cancelable: false } : r));
      return { estado: 200, cuerpo: reservas[0] };
    }
    if (ruta === 'GET /api/portal/transportes-andes/') return { estado: 200, cuerpo: EMPRESA_PORTAL };
    return anterior!(peticion, url);
  };
  return llamadas;
}

describe('mis reservas', () => {
  it('lista sus reservas con su historial y cancela solo sin conductor', async () => {
    const { servidor } = montarPanel('/mis-reservas', { email: 'pasajero@andes.example' });
    const llamadas = instalar(servidor);
    const lista = await screen.findByRole('list', { name: 'Mis reservas' });
    const [primera, segunda] = within(lista).getAllByRole('listitem').filter((li) => li.parentElement === lista);
    expect(within(segunda).queryByRole('button', { name: 'Cancelar reserva' })).not.toBeInTheDocument();
    await userEvent.click(within(primera).getByRole('button', { name: 'Cancelar reserva' }));
    await waitFor(() => expect(llamadas).toContain('POST /api/mi-cuenta/reservas/1/cancelar/'));
    expect(await screen.findByText(/Cancelado/)).toBeInTheDocument();
  });

  it('pide un viaje con sus datos fijos, sin campos de nombre ni WhatsApp', async () => {
    const { servidor } = montarPanel('/mis-reservas', { email: 'pasajero@andes.example' });
    instalar(servidor);
    await userEvent.click(await screen.findByRole('button', { name: 'Pedir un viaje' }));
    expect(await screen.findByText(/A nombre de/)).toHaveTextContent('A nombre de Pablo Pasajero · WhatsApp +56 9 8765 4321');
    expect(screen.queryByLabelText('WhatsApp')).not.toBeInTheDocument();
  });

  it('eliminar la cuenta pide confirmar y cierra la sesión', async () => {
    const { servidor, router } = montarPanel('/mis-reservas', { email: 'pasajero@andes.example' });
    const llamadas = instalar(servidor);
    await userEvent.click(await screen.findByRole('button', { name: 'Eliminar mi cuenta…' }));
    await userEvent.click(screen.getByRole('button', { name: 'Sí, eliminar mi cuenta' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(llamadas).toContain('DELETE /api/mi-cuenta/');
  });
});

// Crear cuenta (HU-35 con el diseño de HU-38): src/paginas/acceso.test.tsx.

describe('recuperar la contraseña', () => {
  function montarPublica(ruta: string, respuestas: Record<string, number>) {
    const servidor = new ServidorPortalFalso();
    const recibidas: string[] = [];
    servidor.fetch = async (entrada, init) => {
      const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
      const camino = new URL(peticion.url).pathname;
      recibidas.push(camino);
      const estado = respuestas[camino] ?? 404;
      return new Response(estado === 400 ? JSON.stringify({ token: ['El enlace no es válido o ya venció. Pide uno nuevo.'] }) : null, {
        status: estado,
        headers: { 'Content-Type': 'application/json' },
      });
    };
    const { entorno } = crearEntorno({ servidor, locks: crearLocks(), ahora: servidor.ahora });
    const rutas = crearRutas();
    const router = createMemoryRouter(rutas, { initialEntries: [ruta] });
    render(<App entorno={entorno} rutas={rutas} router={router} />);
    return recibidas;
  }

  it('pide el enlace y responde lo mismo exista o no', async () => {
    const recibidas = montarPublica('/recuperar', { '/api/auth/recuperar/': 202 });
    await userEvent.type(await screen.findByLabelText('Correo'), 'paula@correo.example');
    await userEvent.click(screen.getByRole('button', { name: 'Enviar enlace' }));
    expect(await screen.findByRole('status')).toHaveTextContent(/te enviamos un enlace/);
    expect(recibidas).toEqual(['/api/auth/recuperar/']);
  });

  it('elige la nueva con el enlace', async () => {
    montarPublica('/recuperar/MQ/tok-en', { '/api/auth/recuperar/confirmar/': 204 });
    await userEvent.type(await screen.findByLabelText('Contraseña nueva'), 'Otra-Clave-Sintetica');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(await screen.findByRole('status')).toHaveTextContent('Listo');
  });

  it('un enlace vencido lo explica', async () => {
    montarPublica('/recuperar/MQ/tok-en', { '/api/auth/recuperar/confirmar/': 400 });
    await userEvent.type(await screen.findByLabelText('Contraseña nueva'), 'Otra-Clave-Sintetica');
    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('El enlace no es válido o ya venció');
  });
});
