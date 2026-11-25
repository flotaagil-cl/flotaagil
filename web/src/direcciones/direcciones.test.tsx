/** HU-71 (DC-72): campo de dirección con sugerencias (sin red: búsqueda y servidores simulados). */

import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { armarPedido, VALORES_INICIALES } from '../pedido/pedido';
import { montarPanel } from '../pruebas/montar';
import type { Respuesta, ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { CampoDireccionPortal } from './CampoDireccionPortal';
import { buscarConSesion, buscarPublico, ESPERA_MS, type Buscar, type Sugerencia } from './sugerencias';

const SUGERENCIAS: Sugerencia[] = [
  { texto: 'Av. Providencia 1234, Providencia', lat: -33.4255, lon: -70.6105 },
  { texto: 'Av. Providencia 2000, Providencia', lat: -33.421, lon: -70.605 },
  { texto: 'Providencia 99, Ñuñoa', lat: -33.45, lon: -70.6 },
];

function Prueba({ buscar, alElegir = vi.fn(), alEnviar = vi.fn() }: { buscar: Buscar; alElegir?: (s: Sugerencia) => void; alEnviar?: () => void }) {
  const [valor, setValor] = useState('');
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        alEnviar();
      }}
    >
      <CampoDireccionPortal
        etiqueta="Origen"
        valor={valor}
        alCambiar={setValor}
        alElegir={(s) => {
          setValor(s.texto);
          alElegir(s);
        }}
        buscar={buscar}
      />
    </form>
  );
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('campo con sugerencias', () => {
  it('desde 3 caracteres y 300 ms después de la última tecla, una sola búsqueda', async () => {
    // Reloj totalmente falso: con la máquina cargada, el tiempo real no puede adelantar la espera.
    vi.useFakeTimers();
    const buscar = vi.fn<Buscar>(async () => SUGERENCIAS);
    render(<Prueba buscar={buscar} />);
    const campo = screen.getByRole('combobox', { name: 'Origen' });
    fireEvent.change(campo, { target: { value: 'pr' } });
    await act(() => vi.advanceTimersByTimeAsync(ESPERA_MS + 50));
    expect(buscar).not.toHaveBeenCalled();
    fireEvent.change(campo, { target: { value: 'pro' } });
    await act(() => vi.advanceTimersByTimeAsync(100));
    fireEvent.change(campo, { target: { value: 'prov' } });
    await act(() => vi.advanceTimersByTimeAsync(ESPERA_MS - 10));
    expect(buscar).not.toHaveBeenCalled();
    await act(() => vi.advanceTimersByTimeAsync(20));
    expect(buscar).toHaveBeenCalledTimes(1);
    expect(buscar.mock.calls[0][0]).toBe('prov');
    expect(screen.getAllByRole('option')).toHaveLength(3);
    expect(campo).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('© OpenStreetMap contributors')).toBeInTheDocument();
  });

  it('teclado: flechas, Enter elige (sin enviar) y Escape cierra', async () => {
    const alElegir = vi.fn();
    const usuario = userEvent.setup();
    render(<Prueba buscar={async () => SUGERENCIAS} alElegir={alElegir} />);
    const campo = screen.getByRole('combobox', { name: 'Origen' });
    await usuario.type(campo, 'prov');
    const lista = await screen.findByRole('listbox', { name: 'Sugerencias de direcciones' }, { timeout: 3000 });
    await usuario.keyboard('{ArrowDown}{ArrowDown}');
    const opciones = within(lista).getAllByRole('option');
    expect(opciones[1]).toHaveAttribute('aria-selected', 'true');
    expect(campo).toHaveAttribute('aria-activedescendant', opciones[1].id);
    await usuario.keyboard('{ArrowUp}{ArrowUp}');
    expect(opciones[2]).toHaveAttribute('aria-selected', 'true'); // vuelve al final
    await usuario.keyboard('{Enter}');
    expect(alElegir).toHaveBeenCalledWith(SUGERENCIAS[2]);
    expect(campo).toHaveValue('Providencia 99, Ñuñoa');
    expect(campo).toHaveAttribute('aria-expanded', 'false');
    // Escape cierra sin elegir.
    await usuario.clear(campo);
    await usuario.type(campo, 'av. p');
    await screen.findAllByRole('option', {}, { timeout: 3000 });
    await usuario.keyboard('{Escape}');
    expect(campo).toHaveAttribute('aria-expanded', 'false');
    expect(alElegir).toHaveBeenCalledTimes(1);
  });

  it('Enter en la dirección nunca envía el formulario: sin lista, con la lista abierta o sin elegir', async () => {
    const alEnviar = vi.fn();
    const alElegir = vi.fn();
    const usuario = userEvent.setup();
    render(<Prueba buscar={async () => SUGERENCIAS} alElegir={alElegir} alEnviar={alEnviar} />);
    const campo = screen.getByRole('combobox', { name: 'Origen' });
    await usuario.type(campo, 'Av{Enter}');
    await usuario.type(campo, 'enida');
    await screen.findAllByRole('option', {}, { timeout: 3000 });
    await usuario.keyboard('{Enter}');
    expect(campo).toHaveAttribute('aria-expanded', 'false');
    await usuario.keyboard('{Enter}');
    expect(alEnviar).not.toHaveBeenCalled();
    expect(alElegir).not.toHaveBeenCalled();
    expect(campo).toHaveValue('Avenida');
  });

  it('con el mouse también se elige', async () => {
    const alElegir = vi.fn();
    render(<Prueba buscar={async () => SUGERENCIAS} alElegir={alElegir} />);
    await userEvent.type(screen.getByRole('combobox', { name: 'Origen' }), 'prov');
    fireEvent.mouseDown((await screen.findAllByRole('option', {}, { timeout: 3000 }))[0]);
    expect(alElegir).toHaveBeenCalledWith(SUGERENCIAS[0]);
  });

  it('si el servicio no responde queda como texto normal, sin errores a la vista', async () => {
    const buscar = vi.fn<Buscar>(async () => {
      throw new TypeError('sin red');
    });
    render(<Prueba buscar={buscar} />);
    const campo = screen.getByRole('combobox', { name: 'Origen' });
    await userEvent.type(campo, 'Los Leones 100');
    await waitFor(() => expect(buscar).toHaveBeenCalled());
    expect(campo).toHaveValue('Los Leones 100');
    expect(campo).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('búsqueda por el backend', () => {
  it('pública: con el slug, filtra lo inválido y hasta 5; sin respuesta ok, nada', async () => {
    const respuestas = [
      new Response(JSON.stringify({ disponible: true, sugerencias: [...SUGERENCIAS, ...SUGERENCIAS, { texto: 1 }] }), { status: 200 }),
      new Response('{}', { status: 429 }),
    ];
    const fetchFalso = vi.fn<(url: string, opciones?: RequestInit) => Promise<Response>>(async () => respuestas.shift()!);
    vi.stubGlobal('fetch', fetchFalso);
    const buscar = buscarPublico('transportes-andes');
    expect(await buscar('prov', new AbortController().signal)).toHaveLength(5);
    expect(String(fetchFalso.mock.calls[0][0])).toBe('/api/direcciones/sugerir/?q=prov&empresa=transportes-andes');
    expect(await buscar('prov', new AbortController().signal)).toEqual([]);
  });

  it('con sesión: usa el cliente del panel; «ninguno» no trae sugerencias', async () => {
    const pedir = vi.fn(async () => ({ data: { disponible: false, sugerencias: [] }, response: new Response(null, { status: 200 }) }));
    expect(await buscarConSesion(pedir)('prov', new AbortController().signal)).toEqual([]);
    expect(pedir).toHaveBeenCalledWith('prov', expect.any(AbortSignal));
  });
});

describe('guardar con las coordenadas de la sugerencia', () => {
  it('pedido del portal: las del origen y destino escritos, no las del aeropuerto fijo', () => {
    const coordenadas = { lat: -33.42, lon: -70.6 };
    const valores = { ...VALORES_INICIALES, origen: 'Los Leones 100', destino: 'Lira 10', origenCoordenadas: coordenadas, destinoCoordenadas: coordenadas, ahora: true };
    const ciudad = armarPedido('en-la-ciudad', valores, { capacidad_maxima: 4 } as never);
    expect('cuerpo' in ciudad && ciudad.cuerpo).toMatchObject({ origen_coordenadas: coordenadas, destino_coordenadas: coordenadas });
    const salida = armarPedido('al-aeropuerto', { ...valores, salidaFecha: '2026-11-20', salidaHora: '08:40' }, { capacidad_maxima: 4, antelacion_vuelo_internacional_min: 180 } as never);
    expect('cuerpo' in salida && salida.cuerpo).toMatchObject({ origen_coordenadas: coordenadas });
    expect('cuerpo' in salida && salida.cuerpo).not.toHaveProperty('destino_coordenadas');
  });

  class ServidorSugerenciasFalso {
    private readonly anterior: ServidorAuthFalso['api'];
    constructor(auth: ServidorAuthFalso) {
      this.anterior = auth.api;
      auth.api = (peticion, url) => this.atender(peticion, url);
    }
    private async atender(peticion: Request, url: URL): Promise<Respuesta> {
      if (url.pathname !== '/api/direcciones/sugerir/') return this.anterior!(peticion, url);
      return { estado: 200, cuerpo: { disponible: true, sugerencias: SUGERENCIAS } };
    }
  }

  it('panel: elegir una sugerencia envía sus coordenadas; escribir a mano después las quita', async () => {
    const contexto = montarPanel('/reservas/nueva');
    new ServidorSugerenciasFalso(contexto.servidor);
    await screen.findByRole('heading', { name: 'Nueva reserva' });
    const usuario = userEvent.setup();
    await usuario.type(screen.getByLabelText('Nombre'), 'Pía Pasajera');
    await usuario.type(screen.getByLabelText('Teléfono (WhatsApp)'), '912345678');
    fireEvent.change(screen.getByLabelText('Recogida'), { target: { value: '2026-11-02T10:00' } });
    const origen = screen.getByRole('combobox', { name: 'Origen' });
    await usuario.type(origen, 'prov');
    await usuario.click((await screen.findAllByRole('option', {}, { timeout: 3000 }))[0]);
    expect(origen).toHaveValue('Av. Providencia 1234, Providencia');
    const destino = screen.getByRole('combobox', { name: 'Destino' });
    await usuario.type(destino, 'prov');
    await usuario.click((await screen.findAllByRole('option', {}, { timeout: 3000 }))[1]);
    await usuario.type(destino, ' depto 5'); // a mano después de elegir: sin coordenadas
    await usuario.click(screen.getByRole('button', { name: 'Guardar reserva' }));
    await waitFor(() => expect(contexto.viajes.cuerpos.some((c) => c.ruta === 'POST /api/viajes/')).toBe(true));
    const cuerpo = contexto.viajes.cuerpos.find((c) => c.ruta === 'POST /api/viajes/')!.cuerpo as Record<string, unknown>;
    expect(cuerpo).toMatchObject({ origen_dir: 'Av. Providencia 1234, Providencia', origen_coordenadas: { lat: -33.4255, lon: -70.6105 } });
    expect(cuerpo.destino_dir).toBe('Av. Providencia 2000, Providencia depto 5');
    expect(cuerpo).not.toHaveProperty('destino_coordenadas');
  });
});
