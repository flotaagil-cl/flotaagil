/**
 * HU-66 (DC-62): botones de emergencia del pasajero: «Llamar a la central» (tel:) y «WhatsApp de la central» (wa.me),
 * con los números que la empresa configuró. Sin números, no se muestra nada. HU-49 (DC-80): sin WhatsApp propio,
 * el botón usa el teléfono de la central, y los números quedan guardados para las pantallas de error.
 */

import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { resultado } from '../api/resultado';
import { useEntorno } from '../entornoContexto';
import { BotonesCentral } from '../componentes/BotonesCentral';
import { guardarCentral } from '../componentes/central';
import { useApi, useSesion } from '../sesion/SesionProvider';

export function ContactoCentral() {
  const api = useApi();
  const { almacen } = useEntorno();
  const { estado } = useSesion();
  const slug = estado.fase === 'autenticada' ? estado.usuario.empresa.slug : '';
  const perfil = useQuery({ queryKey: ['mi-cuenta', 'perfil'], queryFn: () => resultado(api.GET('/api/mi-cuenta/')) });
  const central = perfil.data?.central;
  useEffect(() => {
    if (central) guardarCentral(almacen, slug, central);
  }, [almacen, slug, central]);
  return <BotonesCentral central={central} />;
}
