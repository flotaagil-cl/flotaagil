import { useState } from 'react';
import { Icono } from '../componentes/Icono';

const PUNTOS = [
  {
    titulo: 'Qué se registra',
    texto: 'Tu posición, su precisión y la hora.',
  },
  {
    titulo: 'Cuándo',
    texto: 'Solo en turno (Disponible o En viaje). Verás una notificación fija mientras se registre. Al pasar a No disponible se detiene.',
  },
  {
    titulo: 'Quién la ve',
    texto: 'El despachador y el administrador de tu empresa, en el panel.',
  },
  {
    titulo: 'Cuánto tiempo se guarda',
    texto: '30 días; después se elimina.',
  },
] as const;

/**
 * Consentimiento informado del tratamiento de la ubicación (RN-18). Se acepta una vez y queda registrado en el
 * backend (CONDUCTOR.consentimiento_gps_en); sin él, la ubicación no se registra.
 */
export function Consentimiento({ alAceptar }: { alAceptar: () => Promise<void> }) {
  const [enviando, setEnviando] = useState(false);
  const [falla, setFalla] = useState(false);

  async function aceptar() {
    setEnviando(true);
    setFalla(false);
    try {
      await alAceptar();
    } catch {
      setFalla(true);
      setEnviando(false);
    }
  }

  return (
    <main className="app-pantalla">
      <div className="app-cuerpo consentimiento-cuerpo">
        <div className="consentimiento-cabecera">
          <span className="consentimiento-icono" aria-hidden="true">
            <Icono nombre="ubicacion" tamano={30} />
          </span>
          <h1>Uso de tu ubicación</h1>
          <p className="secundario">Para asignarte viajes y avisar al pasajero, la app registra tu ubicación mientras estás en turno.</p>
        </div>

        <ul className="tarjeta consentimiento-lista">
          {PUNTOS.map((punto) => (
            <li key={punto.titulo} className="consentimiento-item">
              <strong>{punto.titulo}</strong>
              <span>{punto.texto}</span>
            </li>
          ))}
        </ul>

        <p className="aviso alerta-bloque">
          <Icono nombre="ubicacion" tamano={18} />
          <span>Android te pedirá permiso de ubicación y de notificaciones la primera vez que empieces un turno.</span>
        </p>

        {falla && (
          <p className="error alerta-bloque" role="alert">
            <Icono nombre="alerta" tamano={18} />
            <span>No se pudo registrar tu aceptación. Revisa tu conexión e intenta de nuevo.</span>
          </p>
        )}
      </div>

      <footer className="app-pie-barra">
        <button className="principal pie-boton-principal" type="button" onClick={() => void aceptar()} disabled={enviando}>
          {enviando ? 'Guardando…' : 'Acepto'}
        </button>
      </footer>
    </main>
  );
}
