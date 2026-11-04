import { describe, expect, it } from 'vitest';
import { enlaceGoogleMaps, enlaceWaze } from './navegacion';

const aeropuerto = { direccion: 'Aeropuerto SCL', lat: -33.393, lon: -70.7858 };

describe('enlaces de navegación (HU-17)', () => {
  it('Google Maps con destino en coordenadas y modo auto', () => {
    const url = new URL(enlaceGoogleMaps(aeropuerto));
    expect(url.origin + url.pathname).toBe('https://www.google.com/maps/dir/');
    expect(Object.fromEntries(url.searchParams)).toEqual({ api: '1', destination: '-33.393000,-70.785800', travelmode: 'driving' });
  });

  it('Waze con navegación inmediata', () => {
    const url = new URL(enlaceWaze(aeropuerto));
    expect(url.origin + url.pathname).toBe('https://waze.com/ul');
    expect(Object.fromEntries(url.searchParams)).toEqual({ ll: '-33.393000,-70.785800', navigate: 'yes' });
  });
});

describe('navegar con la dirección escrita (DC-30)', () => {
  const punto = { direccion: 'Av. Providencia 1234, Ñuñoa & Cía', lat: -33.43, lon: -70.61 };

  it('Google Maps recibe la dirección, y no las coordenadas', () => {
    const enlace = enlaceGoogleMaps(punto, 'DIRECCION');
    const url = new URL(enlace);
    expect(url.searchParams.get('destination')).toBe(punto.direccion);
    expect(enlace).not.toContain('-33.43');
    expect(url.searchParams.get('travelmode')).toBe('driving');
  });

  it('Waze recibe la dirección en q y sigue navegando de inmediato', () => {
    const enlace = enlaceWaze(punto, 'DIRECCION');
    const url = new URL(enlace);
    expect(Object.fromEntries(url.searchParams)).toEqual({ q: punto.direccion, navigate: 'yes' });
    expect(enlace).not.toContain('ll=');
  });

  it('los espacios y símbolos van codificados', () => {
    const enlace = enlaceWaze(punto, 'DIRECCION');
    expect(enlace).toContain('q=Av.%20Providencia%201234%2C%20%C3%91u%C3%B1oa%20%26%20C%C3%ADa');
    expect(enlace).not.toContain('+');
  });

  it('con coordenadas no envía la dirección', () => {
    expect(enlaceGoogleMaps(punto, 'COORDENADAS')).toContain('destination=-33.430000%2C-70.610000');
    expect(enlaceWaze(punto, 'COORDENADAS')).toContain('ll=-33.430000%2C-70.610000');
    expect(enlaceWaze(punto, 'COORDENADAS')).not.toContain('Providencia');
  });

  it('un backend anterior, sin el campo, sigue con coordenadas', () => {
    expect(enlaceWaze(punto)).toContain('ll=');
    expect(enlaceGoogleMaps(punto)).toContain('destination=-33.430000');
  });
});
