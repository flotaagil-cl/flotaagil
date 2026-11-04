// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { NavegarCon, ViajeActivo } from '../navegacion';
import { ViajeEnCurso } from './ViajeEnCurso';

const abrir = vi.hoisted(() => vi.fn<(opciones: { url: string }) => Promise<{ completed: boolean }>>(async () => ({ completed: true })));
vi.mock('@capacitor/app-launcher', () => ({ AppLauncher: { openUrl: abrir } }));

function viaje(navegar_con: NavegarCon, estado: ViajeActivo['estado'] = 'ACEPTADO'): ViajeActivo {
  const origen = { direccion: 'Plaza de Armas, Santiago', lat: -33.43, lon: -70.65 };
  const destino = { direccion: 'Av. Providencia 1234', lat: -33.42, lon: -70.61 };
  return {
    id: 8,
    estado,
    pasajero: 'Ana Pérez',
    recogida_en: '2026-11-04T15:30:00Z',
    origen,
    destino,
    vuelo: null,
    tarifa: null,
    convenio: false,
    hacia: estado === 'PASAJERO_A_BORDO' ? destino : origen,
    navegar_con,
  };
}

async function urlAlPulsar(boton: string) {
  fireEvent.click(screen.getByRole('button', { name: boton }));
  await waitFor(() => expect(abrir).toHaveBeenCalled());
  return abrir.mock.calls.at(-1)![0].url;
}

afterEach(() => {
  cleanup();
  abrir.mockClear();
});

describe('botones de navegación (DC-30)', () => {
  it('con DIRECCION, Google Maps y Waze reciben la dirección escrita', async () => {
    render(<ViajeEnCurso viaje={viaje('DIRECCION')} />);
    expect(new URL(await urlAlPulsar('Google Maps')).searchParams.get('destination')).toBe('Plaza de Armas, Santiago');
    expect(new URL(await urlAlPulsar('Waze')).searchParams.get('q')).toBe('Plaza de Armas, Santiago');
  });

  it('con COORDENADAS, reciben las coordenadas', async () => {
    render(<ViajeEnCurso viaje={viaje('COORDENADAS')} />);
    expect(new URL(await urlAlPulsar('Google Maps')).searchParams.get('destination')).toBe('-33.430000,-70.650000');
    expect(new URL(await urlAlPulsar('Waze')).searchParams.get('ll')).toBe('-33.430000,-70.650000');
  });

  it('con el pasajero a bordo navega con la dirección del destino', async () => {
    render(<ViajeEnCurso viaje={viaje('DIRECCION', 'PASAJERO_A_BORDO')} />);
    expect(new URL(await urlAlPulsar('Waze')).searchParams.get('q')).toBe('Av. Providencia 1234');
  });

  it('si no se puede abrir, lo dice', async () => {
    abrir.mockRejectedValueOnce(new Error('sin app'));
    render(<ViajeEnCurso viaje={viaje('DIRECCION')} />);
    fireEvent.click(screen.getByRole('button', { name: 'Waze' }));
    expect((await screen.findByRole('alert')).textContent).toBe('No se pudo abrir la navegación.');
  });
});
