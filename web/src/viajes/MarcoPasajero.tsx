import type { ReactNode } from 'react';
import { useNavigate } from 'react-router';
import { MarcoPortal } from '../diseno/MarcoPortal';
import { useSesion } from '../sesion/SesionProvider';
import { ENLACES_PASAJERO } from './viaje';

/** Marco de las pantallas del pasajero con sesión: marca de su empresa, navegación y cerrar sesión. */
export function MarcoPasajero({ barraMovil = 'normal', children }: { barraMovil?: 'normal' | 'flotante' | 'oculta'; children: ReactNode }) {
  const { estado, sesion } = useSesion();
  const navegar = useNavigate();
  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  const salir = () => void sesion.logout().then(() => navegar(`/solicitar/${usuario.empresa.slug}/ingresar`, { replace: true }));
  return (
    <MarcoPortal
      marca={usuario.empresa.razon_social}
      inicio="/pedir"
      enlaces={ENLACES_PASAJERO}
      usuario={usuario}
      onCerrarSesion={salir}
      barraMovil={barraMovil}
    >
      {children}
    </MarcoPortal>
  );
}
