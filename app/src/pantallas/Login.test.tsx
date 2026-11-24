// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { ErrorApi, SinRed, type SesionApp } from '../sesion/sesion';
import { Login } from './Login';

afterEach(cleanup);

function sesionFalsa(overrides: Partial<Pick<SesionApp, 'login' | 'iniciar'>> = {}): SesionApp {
  return {
    login: vi.fn(async () => {}),
    iniciar: vi.fn(async () => {}),
    ...overrides,
  } as unknown as SesionApp;
}

describe('Login de la app del conductor', () => {
  it('muestra marca, campos y mantiene el botón deshabilitado hasta completar ambos', () => {
    render(<Login sesion={sesionFalsa()} />);
    expect(screen.getByRole('heading', { name: 'FlotaÁgil' })).toBeTruthy();
    expect(screen.getByText('App del conductor')).toBeTruthy();

    const correo = screen.getByLabelText('Correo') as HTMLInputElement;
    const clave = screen.getByLabelText('Contraseña') as HTMLInputElement;
    const boton = screen.getByRole('button', { name: 'Ingresar' }) as HTMLButtonElement;

    expect(correo.placeholder).toBe('nombre@empresa.cl');
    expect(clave.type).toBe('password');
    expect(boton.disabled).toBe(true);

    fireEvent.change(correo, { target: { value: '  conductor@andes.cl  ' } });
    expect(boton.disabled).toBe(true);

    fireEvent.change(clave, { target: { value: 'secreta123' } });
    expect(boton.disabled).toBe(false);
  });

  it('permite mostrar y ocultar la contraseña', () => {
    render(<Login sesion={sesionFalsa()} />);
    const clave = screen.getByLabelText('Contraseña') as HTMLInputElement;
    const alternar = screen.getByRole('button', { name: 'Mostrar contraseña' });

    expect(clave.type).toBe('password');
    expect(alternar.getAttribute('aria-pressed')).toBe('false');

    fireEvent.click(alternar);
    expect(clave.type).toBe('text');
    expect(screen.getByRole('button', { name: 'Ocultar contraseña' }).getAttribute('aria-pressed')).toBe('true');

    fireEvent.click(screen.getByRole('button', { name: 'Ocultar contraseña' }));
    expect(clave.type).toBe('password');
  });

  it('recorta espacios del correo al enviar y muestra estado de carga', async () => {
    let resolver!: () => void;
    const login = vi.fn(
      () =>
        new Promise<void>((res) => {
          resolver = res;
        }),
    );
    render(<Login sesion={sesionFalsa({ login })} />);

    fireEvent.change(screen.getByLabelText('Correo'), { target: { value: '  c@andes.cl  ' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'clave' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));

    expect(login).toHaveBeenCalledWith('c@andes.cl', 'clave');
    const enviando = screen.getByRole('button', { name: 'Ingresando…' }) as HTMLButtonElement;
    expect(enviando.disabled).toBe(true);

    resolver();
    await waitFor(() => expect(login).toHaveBeenCalledTimes(1));
  });

  it('muestra mensajes claros para errores de API y de red', async () => {
    const login = vi
      .fn()
      .mockRejectedValueOnce(new ErrorApi(401, { code: 'credenciales_invalidas' }))
      .mockRejectedValueOnce(new ErrorApi(403, { code: 'rol_no_permitido' }))
      .mockRejectedValueOnce(new SinRed());

    render(<Login sesion={sesionFalsa({ login })} />);
    fireEvent.change(screen.getByLabelText('Correo'), { target: { value: 'c@andes.cl' } });
    fireEvent.change(screen.getByLabelText('Contraseña'), { target: { value: 'clave' } });

    fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect((await screen.findByRole('alert')).textContent).toContain('Correo o contraseña incorrectos.');

    fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect((await screen.findByRole('alert')).textContent).toContain('Esta app es solo para conductores.');

    fireEvent.click(screen.getByRole('button', { name: 'Ingresar' }));
    expect((await screen.findByRole('alert')).textContent).toContain('No se pudo conectar con el servidor. Revisa tu conexión.');
  });

  it('muestra avisos por motivo de sesión terminada o sin conexión con reintento', () => {
    const iniciar = vi.fn(async () => {});
    const { rerender } = render(<Login sesion={sesionFalsa({ iniciar })} motivo="sesion_terminada" />);
    expect(screen.getByText('Tu sesión terminó. Ingresa de nuevo.')).toBeTruthy();

    rerender(<Login sesion={sesionFalsa({ iniciar })} motivo="sin_conexion" />);
    expect(screen.getByText(/Sin conexión con el servidor\./)).toBeTruthy();
    fireEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(iniciar).toHaveBeenCalledTimes(1);
  });
});
