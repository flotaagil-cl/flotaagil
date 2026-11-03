import { useState } from 'react';

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
    <main>
      <h1>Uso de tu ubicación</h1>
      <p>Para asignarte viajes y avisar al pasajero, la app registra tu ubicación mientras estás en turno.</p>
      <ul>
        <li>
          <strong>Qué se registra:</strong> tu posición, su precisión y la hora.
        </li>
        <li>
          <strong>Cuándo:</strong> solo en turno (Disponible o En viaje). Verás una notificación fija mientras se
          registre. Al pasar a No disponible se detiene.
        </li>
        <li>
          <strong>Quién la ve:</strong> el despachador y el administrador de tu empresa, en el panel.
        </li>
        <li>
          <strong>Cuánto tiempo se guarda:</strong> 30 días; después se elimina.
        </li>
      </ul>
      <p>Android te pedirá permiso de ubicación y de notificaciones la primera vez que empieces un turno.</p>
      {falla && (
        <p className="error" role="alert">
          No se pudo registrar tu aceptación. Revisa tu conexión e intenta de nuevo.
        </p>
      )}
      <button className="principal" onClick={() => void aceptar()} disabled={enviando}>
        {enviando ? 'Guardando…' : 'Acepto'}
      </button>
    </main>
  );
}
