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
