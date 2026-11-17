import { Navigate } from 'react-router';
import { useContextoPortal } from '../contexto';
import { ReservaPublica } from './ReservaPublica';

/**
 * La dirección que la empresa comparte (/solicitar/:slug). Con el módulo de cuentas (DC-51) lleva al ingreso con su
 * marca (HU-40); sin él, muestra la reserva pública confirmada por correo (HU-51, CC-22).
 */
export function IrAlIngreso() {
  const { empresa, slug } = useContextoPortal();
  if (!empresa.modulo_cuentas) return <ReservaPublica />;
  return <Navigate to={`/solicitar/${slug}/ingresar`} replace />;
}
