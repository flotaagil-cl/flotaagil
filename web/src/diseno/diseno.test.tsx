import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter } from 'react-router';
import { describe, expect, it, vi } from 'vitest';
import { Boton } from './Boton';
import { Campo, DatoFijo } from './Campo';
import { claseBoton, iniciales } from './clases';
import { Contador } from './Contador';
import { Dialogo } from './Dialogo';
import { LineaDeTiempo } from './LineaDeTiempo';
import { Mapa, ProveedorMapa } from './mapa/Mapa';
import { curva, proyectar } from './mapa/proyeccion';
import type { PropsMapa } from './mapa/tipos';
import { MarcoPortal } from './MarcoPortal';
import { PantallaConMapa } from './PantallaConMapa';
import { Pestanas } from './Pestanas';
import { Destacado, Insignia, Tarjeta } from './Tarjeta';

const SCL = { lat: -33.393, lng: -70.794 };
const CENTRO = { lat: -33.437, lng: -70.65 };

describe('HU-37 · componentes del portal', () => {
  it('Campo: etiqueta asociada, error fuera de la etiqueta y descrito', () => {
    render(<Campo etiqueta="Número de vuelo" ayuda="Ej.: LA 845" error="Ingresa el vuelo." />);
    const campo = screen.getByLabelText('Número de vuelo');
    expect(campo).toHaveAccessibleName('Número de vuelo');
    expect(campo).toHaveAttribute('aria-invalid', 'true');
    expect(campo).toHaveAccessibleDescription('Ej.: LA 845 Ingresa el vuelo.');
  });

  it('Campo sin error no se marca inválido; DatoFijo dice que no se puede cambiar', () => {
    render(
      <>
        <Campo etiqueta="Correo" icono="mensaje" />
        <DatoFijo etiqueta="Origen" valor="Aeropuerto de Santiago (SCL)" />
      </>,
    );
    expect(screen.getByLabelText('Correo')).not.toHaveAttribute('aria-invalid');
    expect(screen.getByText('Aeropuerto de Santiago (SCL)')).toBeInTheDocument();
    expect(screen.getByText('(no se puede cambiar)')).toBeInTheDocument();
  });

  it('Boton: cargando lo deshabilita y lo anuncia; claseBoton sirve para enlaces', () => {
    render(
      <Boton cargando ancho>
        Pedir mi traslado
      </Boton>,
    );
    const boton = screen.getByRole('button', { name: 'Pedir mi traslado' });
    expect(boton).toBeDisabled();
    expect(boton).toHaveAttribute('aria-busy', 'true');
    expect(boton).toHaveAttribute('type', 'button');
    expect(claseBoton('texto').split(' ')).toHaveLength(2);
    expect(claseBoton('principal', true).split(' ')).toHaveLength(3);
  });

  it('Insignia, Tarjeta y Destacado muestran su texto', () => {
    render(
      <Tarjeta como="section" aria-labelledby="t">
        <h2 id="t">Vuelo LA 845</h2>
        <Insignia tono="revision">En revisión</Insignia>
        <Destacado titulo="Seguimos tu vuelo por ti">Si se atrasa, tu conductor ya lo sabe.</Destacado>
      </Tarjeta>,
    );
    expect(screen.getByRole('region', { name: 'Vuelo LA 845' })).toBeInTheDocument();
    expect(screen.getByText('En revisión')).toHaveAttribute('data-tono', 'revision');
    expect(screen.getByText('Seguimos tu vuelo por ti')).toBeInTheDocument();
  });

  it('LineaDeTiempo: el paso en curso lleva aria-current y cada paso dice su estado', () => {
    render(
      <LineaDeTiempo
        etiqueta="Estado del viaje"
        pasos={[
          { titulo: 'Pedido confirmado', estado: 'hecho', detalle: 'Mié 12 nov · 21:14' },
          { titulo: 'En camino', estado: 'actual' },
          { titulo: 'Viaje finalizado', estado: 'pendiente' },
        ]}
      />,
    );
    const lista = screen.getByRole('list', { name: 'Estado del viaje' });
    const pasos = within(lista).getAllByRole('listitem');
    expect(pasos[1]).toHaveAttribute('aria-current', 'step');
    expect(pasos[0]).not.toHaveAttribute('aria-current');
    expect(pasos[0]).toHaveTextContent('Pedido confirmado (listo)');
    expect(pasos[2]).toHaveTextContent('(pendiente)');
  });

  it('Contador: respeta mínimo y máximo y anuncia el valor', async () => {
    const usuario = userEvent.setup();
    function Prueba() {
      const [valor, setValor] = useState(1);
      return <Contador etiqueta="Pasajeros" unidad="un pasajero" valor={valor} min={1} max={2} onCambiar={setValor} error="Máximo 2." />;
    }
    render(<Prueba />);
    const grupo = screen.getByRole('group', { name: 'Pasajeros' });
    expect(grupo).toHaveAccessibleDescription('Máximo 2.');
    const quitar = screen.getByRole('button', { name: 'Quitar un pasajero' });
    const agregar = screen.getByRole('button', { name: 'Agregar un pasajero' });
    expect(quitar).toBeDisabled();
    await usuario.click(agregar);
    expect(within(grupo).getByRole('status')).toHaveTextContent('2');
    expect(agregar).toBeDisabled();
    await usuario.click(quitar);
    expect(within(grupo).getByRole('status')).toHaveTextContent('1');
  });

  it('Pestanas: flechas, Inicio y Fin cambian la pestaña y mueven el foco', async () => {
    const usuario = userEvent.setup();
    function Prueba() {
      const [activa, setActiva] = useState('desde');
      const pestanas = [
        { id: 'desde', titulo: 'Desde el aeropuerto' },
        { id: 'al', titulo: 'Al aeropuerto' },
        { id: 'ciudad', titulo: 'En la ciudad' },
      ];
      return (
        <Pestanas etiqueta="Tipo de viaje" pestanas={pestanas} activa={activa} onCambiar={setActiva}>
          <p>Panel {activa}</p>
        </Pestanas>
      );
    }
    render(<Prueba />);
    const desde = screen.getByRole('tab', { name: 'Desde el aeropuerto' });
    expect(desde).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tabpanel', { name: 'Desde el aeropuerto' })).toHaveTextContent('Panel desde');
    await usuario.click(desde);
    await usuario.keyboard('{ArrowLeft}');
    expect(screen.getByRole('tab', { name: 'En la ciudad' })).toHaveFocus();
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Panel ciudad');
    await usuario.keyboard('{Home}');
    expect(desde).toHaveFocus();
    await usuario.keyboard('{End}{ArrowRight}');
    expect(desde).toHaveAttribute('aria-selected', 'true');
    await usuario.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Al aeropuerto' })).toHaveAttribute('tabindex', '0');
    await usuario.keyboard('a');
    expect(screen.getByRole('tab', { name: 'Al aeropuerto' })).toHaveFocus();
  });

  it('Dialogo: aria-modal, foco adentro, Tab no sale, Esc cierra y el foco vuelve', async () => {
    const usuario = userEvent.setup();
    function Prueba() {
      const [abierto, setAbierto] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setAbierto(true)}>
            Cancelar viaje
          </button>
          <Dialogo abierto={abierto} titulo="¿Cancelar tu viaje?" onCerrar={() => setAbierto(false)}>
            <button type="button">Sí, cancelar</button>
            <button type="button">Volver</button>
          </Dialogo>
        </>
      );
    }
    render(<Prueba />);
    const abrir = screen.getByRole('button', { name: 'Cancelar viaje' });
    await usuario.click(abrir);
    const dialogo = screen.getByRole('dialog', { name: '¿Cancelar tu viaje?' });
    expect(dialogo).toHaveAttribute('aria-modal', 'true');
    expect(screen.getByRole('button', { name: 'Sí, cancelar' })).toHaveFocus();
    await usuario.tab();
    expect(screen.getByRole('button', { name: 'Volver' })).toHaveFocus();
    await usuario.tab();
    expect(screen.getByRole('button', { name: 'Cerrar' })).toHaveFocus();
    await usuario.tab({ shift: true });
    expect(screen.getByRole('button', { name: 'Volver' })).toHaveFocus();
    await usuario.keyboard('{Escape}');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(abrir).toHaveFocus();
  });

  it('Dialogo: cierra con el botón Cerrar y tocando fuera, no tocando adentro', async () => {
    const usuario = userEvent.setup();
    const cerrar = vi.fn();
    render(
      <Dialogo abierto titulo="Aviso" onCerrar={cerrar}>
        <p>Texto</p>
      </Dialogo>,
    );
    await usuario.click(screen.getByText('Texto'));
    expect(cerrar).not.toHaveBeenCalled();
    await usuario.click(screen.getByRole('button', { name: 'Cerrar' }));
    await usuario.click(screen.getByRole('dialog').parentElement!);
    expect(cerrar).toHaveBeenCalledTimes(2);
  });

  it('iniciales: dos primeras palabras', () => {
    expect(iniciales('Transportes Andes SpA')).toBe('TA');
    expect(iniciales('  camila  ')).toBe('C');
  });
});

describe('HU-37 · marco y pantalla con mapa', () => {
  it('MarcoPortal: marca, navegación, salto al contenido y menú de la cuenta', async () => {
    const usuario = userEvent.setup();
    const salir = vi.fn();
    render(
      <MemoryRouter initialEntries={['/pedir']}>
        <MarcoPortal
          marca="Transportes Andes"
          inicio="/pedir"
          enlaces={[
            { a: '/pedir', texto: 'Pedir traslado' },
            { a: '/mis-viajes', texto: 'Mis viajes' },
          ]}
          usuario={{ nombre: 'Camila Muñoz' }}
          onCerrarSesion={salir}
          colores={{ '--color-primario-700': 'teal' }}
        >
          <h1>¿A dónde te llevamos?</h1>
        </MarcoPortal>
      </MemoryRouter>,
    );
    expect(screen.getByRole('link', { name: 'Transportes Andes' })).toHaveAttribute('href', '/pedir');
    const principal = screen.getByRole('navigation', { name: 'Principal' });
    expect(within(principal).getByRole('link', { name: 'Pedir traslado' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Saltar al contenido' })).toHaveAttribute('href', '#contenido');
    expect(screen.getByRole('main')).toHaveAttribute('id', 'contenido');
    expect(screen.getByRole('main').parentElement).toHaveClass('tema-portal');
    expect(screen.getByRole('main').parentElement!.style.getPropertyValue('--color-primario-700')).toBe('teal');

    const cuenta = screen.getByRole('button', { name: /Camila Muñoz/ });
    expect(cuenta).toHaveAttribute('aria-expanded', 'false');
    await usuario.click(cuenta);
    const menu = screen.getByRole('dialog', { name: 'Tu cuenta' });
    await usuario.click(within(menu).getByRole('link', { name: 'Mis viajes' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await usuario.click(cuenta);
    await usuario.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(salir).toHaveBeenCalledOnce();
  });

  it('MarcoPortal sin sesión: sin navegación ni cuenta', () => {
    render(
      <MemoryRouter>
        <MarcoPortal marca="Transportes Andes">
          <p>Ingresar</p>
        </MarcoPortal>
      </MemoryRouter>,
    );
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('PantallaConMapa: el contenido va antes que el mapa; volver y estado', () => {
    render(
      <MemoryRouter>
        <PantallaConMapa
          volver={{ a: '/inicio', texto: 'Volver al inicio' }}
          estado="SCL · Llegadas"
          mapa={<Mapa etiqueta="Mapa del traslado" marcadores={[{ id: 'scl', punto: SCL, tipo: 'aeropuerto', etiqueta: 'SCL' }]} />}
        >
          <h1>Desde el aeropuerto</h1>
        </PantallaConMapa>
      </MemoryRouter>,
    );
    const titulo = screen.getByRole('heading', { name: 'Desde el aeropuerto' });
    const mapa = screen.getByRole('img', { name: 'Mapa del traslado' });
    expect(titulo.compareDocumentPosition(mapa) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    // En el computador el botón volver está oculto (están las pestañas); en el celular se muestra.
    expect(document.querySelector('a[href="/inicio"]')).toHaveAttribute('aria-label', 'Volver al inicio');
    expect(screen.getByText('SCL · Llegadas')).toBeInTheDocument();
  });
});

describe('HU-37 · mapa de respaldo y adaptador', () => {
  const marcadores: PropsMapa['marcadores'] = [
    { id: 'scl', punto: SCL, tipo: 'aeropuerto', etiqueta: 'Aeropuerto' },
    { id: 'destino', punto: CENTRO, tipo: 'destino', etiqueta: 'Destino' },
    { id: 'v1', punto: { lat: -33.42, lng: -70.7 }, tipo: 'vehiculo', etiqueta: 'Vehículo' },
    { id: 'yo', punto: { lat: -33.45, lng: -70.66 }, tipo: 'origen', etiqueta: 'Origen' },
  ];

  it('sin proveedor dibuja el de respaldo con sus pines y la ruta', () => {
    const { container } = render(<Mapa etiqueta="Mapa: aeropuerto y destino" marcadores={marcadores} ruta={{ desde: SCL, hasta: CENTRO }} />);
    expect(screen.getByRole('img', { name: 'Mapa: aeropuerto y destino' })).toBeInTheDocument();
    for (const tipo of ['aeropuerto', 'destino', 'vehiculo', 'origen']) {
      expect(container.querySelector(`[data-tipo="${tipo}"]`)).not.toBeNull();
    }
    expect(container.querySelector('title')?.textContent).toBe('Aeropuerto');
  });

  it('el proveedor lo reemplaza por otro mapa sin tocar la pantalla', () => {
    function MapaReal({ etiqueta, marcadores: m }: PropsMapa) {
      return <div role="img" aria-label={`${etiqueta} (real, ${m.length} pines)`} />;
    }
    render(
      <ProveedorMapa componente={MapaReal}>
        <Mapa etiqueta="Mapa" marcadores={marcadores} />
      </ProveedorMapa>,
    );
    expect(screen.getByRole('img', { name: 'Mapa (real, 4 pines)' })).toBeInTheDocument();
  });

  it('proyectar: norte arriba, este a la derecha, dentro del lienzo; sin puntos o uno solo, al centro', () => {
    const ubicar = proyectar([SCL, CENTRO]);
    const a = ubicar(SCL);
    const b = ubicar(CENTRO);
    expect(a.y).toBeLessThan(b.y); // SCL está más al norte
    expect(a.x).toBeLessThan(b.x); // y más al oeste
    for (const p of [a, b]) {
      expect(p.x).toBeGreaterThanOrEqual(0);
      expect(p.x).toBeLessThanOrEqual(400);
      expect(p.y).toBeGreaterThanOrEqual(0);
      expect(p.y).toBeLessThanOrEqual(300);
    }
    expect(proyectar([])(SCL)).toEqual({ x: 200, y: 150 });
    expect(proyectar([SCL])(SCL)).toEqual({ x: 200, y: 150 });
    expect(curva({ x: 0, y: 0 }, { x: 10, y: 0 })).toBe('M0 0 Q5 -2 10 0');
  });
});
