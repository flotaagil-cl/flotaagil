import { useEffect, useState } from 'react';

/** HU-69: hora actual que se renueva sola, para las cuentas regresivas de los vuelos. */
export function useAhora(cadaMs = 30_000): number {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const reloj = window.setInterval(() => setAhora(Date.now()), cadaMs);
    return () => window.clearInterval(reloj);
  }, [cadaMs]);
  return ahora;
}
