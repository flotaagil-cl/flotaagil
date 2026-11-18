/**
 * HU-66 (DC-62): botones de emergencia del pasajero: «Llamar a la central» (tel:) y «WhatsApp de la central» (wa.me),
 * con los números que la empresa configuró. Sin números, no se muestra nada.
 */

import { useQuery } from '@tanstack/react-query';
import { resultado } from '../api/resultado';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { useApi } from '../sesion/SesionProvider';

export function ContactoCentral() {
  const api = useApi();
  const perfil = useQuery({ queryKey: ['mi-cuenta', 'perfil'], queryFn: () => resultado(api.GET('/api/mi-cuenta/')) });
  const central = perfil.data?.central;
  if (!central?.telefono && !central?.whatsapp) return null;
  return (
    <div className={e.formulario} role="group" aria-label="Contactar a la central">
      {central.telefono && (
        <a href={`tel:${central.telefono}`} className={claseBoton('secundario', true)}>
          Llamar a la central
        </a>
      )}
      {central.whatsapp && (
        <a href={`https://wa.me/${central.whatsapp.replace(/\D/g, '')}`} target="_blank" rel="noreferrer" className={claseBoton('secundario', true)}>
          WhatsApp de la central
        </a>
      )}
    </div>
  );
}
