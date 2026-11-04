/** HU-01: indicadores de Inicio, actualizados por el aviso del WebSocket. */

import { act, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { montarPanel } from '../pruebas/montar';

class SocketFalso {
  static creados: SocketFalso[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((evento: { data: string }) => void) | null = null;
  onclose: ((evento: { code: number }) => void) | null = null;
  readonly url: string;
  readonly protocolos: string[];
  cerrado = false;
  constructor(url: string, protocolos: string[]) {
    this.url = url;
    this.protocolos = protocolos;
    SocketFalso.creados.push(this);
  }
  close() {
    this.cerrado = true;
  }
}

const delIndicadores = () => SocketFalso.creados.filter((s) => s.url.endsWith('/ws/indicadores/'));
const POR_ESTADO = ['PENDIENTE_CONFIRMACION', 'SOLICITADO', 'ASIGNADO', 'ACEPTADO', 'EN_CAMINO', 'EN_ZONA', 'PASAJERO_A_BORDO', 'FINALIZADO', 'CANCELADO'] as const;

function indicadores(solicitadas: number, enLinea: number) {
  return {
    fecha: '2026-07-15',
    reservas: { total: solicitadas, por_estado: POR_ESTADO.map((estado) => ({ estado, cantidad: estado === 'SOLICITADO' ? solicitadas : 0 })) },
    vehiculos: { en_linea: enLinea, fuera_de_linea: 3 },
  };
}

function montar(valor = indicadores(2, 1)) {
  const contexto = montarPanel('/');
  contexto.viajes.indicadores = valor;
  return contexto;
}

beforeEach(() => {
  SocketFalso.creados = [];
  vi.stubGlobal('WebSocket', SocketFalso);
});

describe('indicadores (HU-01)', () => {
  it('muestra los vehículos y las reservas del día por estado, con enlace al listado filtrado', async () => {
    montar();
    expect(await screen.findByText('Vehículos en línea')).toBeInTheDocument();
    expect(screen.getByText('Vehículos en línea').parentElement).toHaveTextContent('1');
    expect(screen.getByText('Vehículos fuera de línea').parentElement).toHaveTextContent('3');
    expect(screen.getByText('Reservas del día').parentElement).toHaveTextContent('2');
    const lista = screen.getByRole('list', { name: 'Reservas del día por estado' });
    expect(within(lista).getAllByRole('listitem')).toHaveLength(9);
    const solicitado = within(lista).getByRole('link', { name: /Solicitado/ });
    expect(solicitado).toHaveTextContent('2');
    expect(solicitado).toHaveAttribute('href', '/reservas?fecha=2026-07-15&estado=SOLICITADO');
  });

  it('se conecta con el access como subprotocolo', async () => {
    montar();
    await waitFor(() => expect(delIndicadores()).toHaveLength(1));
    expect(delIndicadores()[0].protocolos[0]).toBe('flotaagil');
    expect(delIndicadores()[0].protocolos[1]).toBeTruthy();
  });

  it('un aviso actualiza los números sin recargar', async () => {
    const { viajes } = montar();
    await screen.findByText('Vehículos en línea');
    await waitFor(() => expect(delIndicadores()).toHaveLength(1));
    act(() => delIndicadores()[0].onopen?.());
    expect(await screen.findByText('En vivo')).toBeInTheDocument();
    viajes.indicadores = indicadores(7, 4);
    act(() => delIndicadores()[0].onmessage?.({ data: '{"tipo":"cambio"}' }));
    await waitFor(() => expect(screen.getByText('Reservas del día').parentElement).toHaveTextContent('7'));
    expect(screen.getByText('Vehículos en línea').parentElement).toHaveTextContent('4');
  });

  it('al perder la conexión lo dice y sigue mostrando los datos', async () => {
    montar();
    await screen.findByText('Vehículos en línea');
    await waitFor(() => expect(delIndicadores()).toHaveLength(1));
    act(() => delIndicadores()[0].onclose?.({ code: 1006 }));
    expect(await screen.findByText(/Reconectando/)).toBeInTheDocument();
    expect(screen.getByText('Vehículos en línea')).toBeInTheDocument();
  });

  it('con el access vencido (4401) renueva y se reconecta al instante', async () => {
    montar();
    await waitFor(() => expect(delIndicadores()).toHaveLength(1));
    act(() => delIndicadores()[0].onclose?.({ code: 4401 }));
    await waitFor(() => expect(delIndicadores()).toHaveLength(2));
  });

  it('una falla de carga ofrece reintentar', async () => {
    const { viajes } = montar();
    viajes.siguiente('GET /api/indicadores/', { estado: 500, cuerpo: {} });
    await userEvent.click(await screen.findByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('Vehículos en línea')).toBeInTheDocument();
  });

  it('al salir de Inicio cierra la conexión', async () => {
    const { router } = montar();
    await waitFor(() => expect(delIndicadores()).toHaveLength(1));
    await act(async () => {
      await router.navigate('/reservas');
    });
    await waitFor(() => expect(delIndicadores()[0].cerrado).toBe(true));
  });
});
