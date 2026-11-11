/** HU-39: inicio y pedido del pasajero en tres tipos. */

import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';
import { ServidorAuthFalso } from '../pruebas/servidorAuthFalso';
import { EMPRESA_PORTAL } from '../pruebas/servidorPortalFalso';
import { armarPedido, erroresDelServidor, horaDe, recogidaSugerida, textoAntelacion, VALORES_INICIALES, type EmpresaPublica } from './pedido';

const EMPRESA: EmpresaPublica = { ...EMPRESA_PORTAL, capacidad_maxima: 4 };
const json = (estado: number, cuerpo: unknown) => new Response(JSON.stringify(cuerpo), { status: estado, headers: { 'Content-Type': 'application/json' } });

function montarPedido(ruta = '/pedir', respuestas: (() => Response)[] = []) {
  const servidor = new ServidorAuthFalso();
  const enviados: unknown[] = [];
  const original = servidor.fetch;
  servidor.fetch = async (entrada, init) => {
    const peticion = entrada instanceof Request ? entrada : new Request(entrada, init);
    const { pathname } = new URL(peticion.url);
    if (pathname === '/api/portal/transportes-andes/') return json(200, EMPRESA);
    if (pathname === '/api/mi-cuenta/solicitudes/') {
      enviados.push(await peticion.json());
      const siguiente = respuestas.shift();
      return siguiente ? siguiente() : json(201, { estado: 'SOLICITADO', recogida_en: '2026-11-12T12:00:00Z', expira_en: null, mensaje: 'ok' });
    }
    return original(peticion);
  };
  const contexto = montarPanel(ruta, { email: 'pasajero@andes.example', servidor });
  return { ...contexto, enviados };
}

function angosto(si: boolean) {
  vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: si, media: consulta, addEventListener: () => {}, removeEventListener: () => {} }));
}

afterEach(() => vi.unstubAllGlobals());

describe('HU-39 · armar el pedido', () => {
  it('desde el aeropuerto: SCL fijo, vuelo con número y fecha', () => {
    const armado = armarPedido('desde-aeropuerto', { ...VALORES_INICIALES, vueloNumero: 'la 845', vueloFecha: '2026-11-20', destino: ' Av. Apoquindo 3000 ', pasajeros: 2, maletas: 3 }, EMPRESA);
    expect(armado).toEqual({
      cuerpo: {
        pasajeros: 2,
        maletas: 3,
        sentido: 'DESDE_AEROPUERTO',
        origen_dir: 'Aeropuerto de Santiago (SCL)',
        destino_dir: 'Av. Apoquindo 3000',
        vuelo: { numero: 'LA 845', fecha: '2026-11-20' },
      },
    });
  });

  it('desde el aeropuerto con la hora pedida por el servidor: la envía en hora de Chile', () => {
    const armado = armarPedido('desde-aeropuerto', { ...VALORES_INICIALES, vueloNumero: 'LA845', vueloFecha: '2026-11-20', vueloHora: '19:05', destino: 'Centro' }, EMPRESA);
    expect('cuerpo' in armado && armado.cuerpo.vuelo).toEqual({ numero: 'LA845', hora_llegada: '2026-11-20T22:05:00.000Z' });
  });

  it('desde el aeropuerto: obligatorios y formato del vuelo', () => {
    expect(armarPedido('desde-aeropuerto', VALORES_INICIALES, EMPRESA)).toEqual({
      errores: { vueloNumero: 'Ingresa el número de vuelo.', vueloFecha: 'Indica la fecha del vuelo.', destino: 'Ingresa la dirección de destino.' },
    });
    const malo = armarPedido('desde-aeropuerto', { ...VALORES_INICIALES, vueloNumero: 'VUELO-1', vueloFecha: '2026-11-20', destino: 'x', vueloHora: '99:99' }, EMPRESA);
    expect(malo).toEqual({ errores: { vueloNumero: 'Revisa el número: por ejemplo, LA 845.', vueloHora: 'Ingresa una hora válida.' } });
  });

  it('al aeropuerto: vuelo de salida y recogida sugerida (3 h internacional, 2 h nacional)', () => {
    const valores = { ...VALORES_INICIALES, origen: 'Los Leones 100', salidaFecha: '2026-11-20', salidaHora: '08:40' };
    const internacional = recogidaSugerida(valores, EMPRESA)!;
    expect(horaDe(internacional)).toBe('05:40');
    expect(horaDe(recogidaSugerida({ ...valores, salidaTipo: 'NACIONAL' }, EMPRESA)!)).toBe('06:40');
    expect(recogidaSugerida(VALORES_INICIALES, EMPRESA)).toBeNull();
    expect(armarPedido('al-aeropuerto', valores, EMPRESA)).toEqual({
      cuerpo: expect.objectContaining({
        sentido: 'HACIA_AEROPUERTO',
        origen_dir: 'Los Leones 100',
        destino_dir: 'Aeropuerto de Santiago (SCL)',
        vuelo_salida: { hora: '2026-11-20T11:40:00.000Z', tipo: 'INTERNACIONAL' },
      }),
    });
  });

  it('al aeropuerto: la recogida cambiada se envía; sin datos, errores', () => {
    const valores = { ...VALORES_INICIALES, origen: 'x', salidaFecha: '2026-11-20', salidaHora: '08:40', cambiarRecogida: true, recogidaFecha: '2026-11-20', recogidaHora: '05:00' };
    const armado = armarPedido('al-aeropuerto', valores, EMPRESA);
    expect('cuerpo' in armado && armado.cuerpo.recogida_en).toBe('2026-11-20T08:00:00.000Z');
    expect(armarPedido('al-aeropuerto', { ...valores, recogidaHora: '' }, EMPRESA)).toEqual({ errores: { recogidaHora: 'Indica la fecha y hora de recogida.' } });
    expect(armarPedido('al-aeropuerto', VALORES_INICIALES, EMPRESA)).toEqual({
      errores: { origen: 'Ingresa la dirección de recogida.', salidaFecha: 'Indica la fecha del vuelo.', salidaHora: 'Indica la hora de salida.' },
    });
  });

  it('en la ciudad: lo antes posible o programado; pasajeros sobre la capacidad', () => {
    const valores = { ...VALORES_INICIALES, origen: 'A', destino: 'B' };
    expect(armarPedido('en-la-ciudad', valores, EMPRESA)).toEqual({ cuerpo: expect.objectContaining({ sentido: 'URBANO', lo_antes_posible: true }) });
    const programado = armarPedido('en-la-ciudad', { ...valores, ahora: false, recogidaFecha: '2026-11-20', recogidaHora: '10:00' }, EMPRESA);
    expect('cuerpo' in programado && programado.cuerpo.recogida_en).toBe('2026-11-20T13:00:00.000Z');
    expect(armarPedido('en-la-ciudad', { ...valores, ahora: false }, EMPRESA)).toEqual({ errores: { recogidaHora: 'Indica la fecha y hora de recogida.' } });
    expect(armarPedido('en-la-ciudad', { ...valores, pasajeros: 5 }, EMPRESA)).toEqual({ errores: { pasajeros: 'Podemos llevar hasta 4 pasajeros en un vehículo.' } });
    expect(armarPedido('en-la-ciudad', { ...valores, pasajeros: 5 }, { ...EMPRESA, capacidad_maxima: 5 })).toHaveProperty('cuerpo');
  });

  it('textos y errores del servidor', () => {
    expect([textoAntelacion(180), textoAntelacion(60), textoAntelacion(90)]).toEqual(['3 horas', '1 hora', '90 minutos']);
    expect(erroresDelServidor({ vuelo: { hora_llegada: ['Indica la hora.'] }, recogida_en: ['Muy pronto.'] })).toEqual({ vueloHora: 'Indica la hora.', recogidaHora: 'Muy pronto.' });
    expect(erroresDelServidor({ vuelo_salida: 'Solo al aeropuerto.' })).toEqual({ salidaHora: 'Solo al aeropuerto.' });
    expect(erroresDelServidor({ detail: 'Otra cosa.' })).toEqual({ general: 'Otra cosa.' });
    expect(erroresDelServidor(null)).toEqual({ general: 'Revisa los datos del pedido.' });
  });
});

describe('HU-39 · pantalla del pedido', () => {
  it('computador: pestañas con los tres tipos y la marca de la empresa del pasajero', async () => {
    const { router } = montarPedido();
    expect(await screen.findByRole('heading', { name: '¿A dónde te llevamos?' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Transportes Andes Demo SpA' })).toHaveAttribute('href', '/pedir');
    const pestanas = screen.getAllByRole('tab').map((p) => p.textContent);
    expect(pestanas).toEqual(['Desde el aeropuerto', 'Al aeropuerto', 'En la ciudad']);
    expect(screen.getByRole('tab', { name: 'Desde el aeropuerto' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getAllByText('Aeropuerto de Santiago (SCL)')[0]).toHaveClass(/datoFijoValor/);
    expect(screen.getByText('Seguimos tu vuelo por ti')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('tab', { name: 'En la ciudad' }));
    expect(router.state.location.pathname).toBe('/pedir/en-la-ciudad');
    expect(await screen.findByText('Te recogemos en unos 30 minutos.')).toBeInTheDocument();
  });

  it('celular: el inicio muestra las tres opciones y cada una lleva a su formulario', async () => {
    angosto(true);
    const { router } = montarPedido();
    expect(await screen.findByRole('heading', { name: '¿Qué viaje necesitas?' })).toBeInTheDocument();
    expect(screen.getByText('Hola, Pablo')).toBeInTheDocument();
    const opciones = within(screen.getByRole('navigation', { name: 'Tipo de viaje' })).getAllByRole('link');
    expect(opciones.map((o) => o.getAttribute('href'))).toEqual(['/pedir/desde-aeropuerto', '/pedir/al-aeropuerto', '/pedir/en-la-ciudad']);
    await userEvent.click(opciones[1]);
    expect(router.state.location.pathname).toBe('/pedir/al-aeropuerto');
    expect(await screen.findByRole('heading', { name: 'Al aeropuerto' })).toBeInTheDocument();
    expect(screen.queryByRole('tab')).not.toBeInTheDocument();
  });

  it('desde el aeropuerto: envía y confirma; si la API no respondió, pide la hora de llegada', async () => {
    const { enviados } = montarPedido('/pedir/desde-aeropuerto', [() => json(400, { vuelo: { hora_llegada: ['No pudimos consultar tu vuelo en este momento. Indica la hora de llegada.'] } })]);
    await userEvent.type(await screen.findByLabelText('Número de vuelo'), 'LA 845');
    fireEvent.change(screen.getByLabelText('Fecha'), { target: { value: '2026-11-20' } });
    await userEvent.type(screen.getByLabelText('¿A dónde vas?'), 'Av. Apoquindo 3000');
    await userEvent.click(screen.getByRole('button', { name: 'Agregar un pasajero' }));
    await userEvent.click(screen.getByRole('button', { name: 'Agregar una maleta' }));
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    const hora = await screen.findByLabelText('Hora de llegada');
    expect(hora).toHaveAccessibleDescription(/Indica la hora de llegada/);
    fireEvent.change(hora, { target: { value: '19:05' } });
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    expect(await screen.findByRole('heading', { name: 'Recibimos tu pedido' })).toBeInTheDocument();
    expect(enviados[0]).toMatchObject({ vuelo: { numero: 'LA 845', fecha: '2026-11-20' }, pasajeros: 2, maletas: 1 });
    expect(enviados[1]).toMatchObject({ vuelo: { numero: 'LA 845', hora_llegada: '2026-11-20T22:05:00.000Z' } });
    await userEvent.click(screen.getByRole('button', { name: 'Pedir otro traslado' }));
    expect(screen.getByLabelText('Número de vuelo')).toHaveValue('');
  });

  it('al aeropuerto: recogida sugerida con «Cambiar»; tipo de vuelo con radios', async () => {
    const { enviados } = montarPedido('/pedir/al-aeropuerto');
    await userEvent.type(await screen.findByLabelText('¿Dónde te recogemos?'), 'Los Leones 100');
    fireEvent.change(screen.getByLabelText('Fecha del vuelo'), { target: { value: '2026-11-20' } });
    fireEvent.change(screen.getByLabelText('Hora de salida'), { target: { value: '08:40' } });
    expect(screen.getByText('Te recogemos a las 05:40')).toBeInTheDocument();
    expect(screen.getByText(/3 horas antes de tu vuelo internacional/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('radio', { name: 'Nacional' }));
    expect(screen.getByText('Te recogemos a las 06:40')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cambiar' }));
    fireEvent.change(screen.getByLabelText('Fecha de recogida'), { target: { value: '2026-11-20' } });
    fireEvent.change(screen.getByLabelText('Hora de recogida'), { target: { value: '06:00' } });
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    await screen.findByRole('heading', { name: 'Recibimos tu pedido' });
    expect(enviados[0]).toMatchObject({ vuelo_salida: { tipo: 'NACIONAL' }, recogida_en: '2026-11-20T09:00:00.000Z', sentido: 'HACIA_AEROPUERTO' });
  });

  it('al aeropuerto: si la sugerida ya pasó, el error del servidor se ve aunque no se haya cambiado', async () => {
    montarPedido('/pedir/al-aeropuerto', [() => json(400, { recogida_en: ['La recogida debe ser al menos 30 minutos después de ahora.'] })]);
    await userEvent.type(await screen.findByLabelText('¿Dónde te recogemos?'), 'Los Leones 100');
    fireEvent.change(screen.getByLabelText('Fecha del vuelo'), { target: { value: '2026-11-20' } });
    fireEvent.change(screen.getByLabelText('Hora de salida'), { target: { value: '08:40' } });
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('al menos 30 minutos');
  });

  it('en la ciudad: lo antes posible por defecto; programar pide fecha y hora; errores 429 y de red', async () => {
    const { enviados } = montarPedido('/pedir/en-la-ciudad', [() => json(429, { detail: 'x' }), () => json(500, {})]);
    await userEvent.type(await screen.findByLabelText('Origen'), 'Av. Providencia 1208');
    await userEvent.type(screen.getByLabelText('Destino'), 'Plaza de Armas');
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Ya pediste varios traslados');
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('No se pudo enviar tu pedido'));
    expect(enviados[0]).toMatchObject({ lo_antes_posible: true });
    await userEvent.click(screen.getByRole('radio', { name: 'Programar' }));
    await userEvent.click(screen.getByRole('button', { name: 'Pedir mi traslado' }));
    expect(screen.getByLabelText('Hora')).toHaveAccessibleDescription('Indica la fecha y hora de recogida.');
    expect(enviados).toHaveLength(2);
  });

  it('los contadores respetan la capacidad máxima de la empresa', async () => {
    montarPedido('/pedir/en-la-ciudad');
    const agregar = await screen.findByRole('button', { name: 'Agregar un pasajero' });
    for (let i = 0; i < 3; i++) await userEvent.click(agregar);
    expect(agregar).toBeDisabled();
  });

  it('un tipo desconocido vuelve a /pedir; otros roles van a su vista', async () => {
    const { router } = montarPedido('/pedir/otra-cosa');
    await waitFor(() => expect(router.state.location.pathname).toBe('/pedir'));
  });

  it('cerrar sesión lleva al ingreso de su empresa', async () => {
    const { router } = montarPedido();
    await userEvent.click(await screen.findByRole('button', { name: /menú de la cuenta/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/solicitar/transportes-andes/ingresar'));
  });
});

describe('HU-39 · otros roles', () => {
  it('el despachador que entra a /pedir vuelve al panel', async () => {
    const { router } = montarPanel('/pedir');
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});
