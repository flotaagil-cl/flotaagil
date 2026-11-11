import { Navigate } from 'react-router';
import { useContextoPortal } from '../contexto';

/**
 * HU-40 (CC-18): ya no se pide sin cuenta. La dirección del portal que la empresa comparte
 * (/solicitar/:slug) lleva al ingreso con su marca.
 */
export function IrAlIngreso() {
  const { slug } = useContextoPortal();
  return <Navigate to={`/solicitar/${slug}/ingresar`} replace />;
}
