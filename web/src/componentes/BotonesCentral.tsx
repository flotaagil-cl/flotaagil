/**
 * HU-66 y HU-49 (DC-62, DC-80): «Llamar a la central» y «WhatsApp de la central». Sin sesión: lo usan también el
 * portal público y las pantallas de error, que no cargan nada de src/sesion/.
 */

import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import '../diseno/tokens.css';
import '../diseno/paletas.css';
import { conWhatsapp, enlaceWhatsapp, hayNumeros, type NumerosCentral } from './central';

/** Los dos botones, con los números que lleguen (del backend o de los guardados). */
export function BotonesCentral({ central }: { central: NumerosCentral | null | undefined }) {
  if (!hayNumeros(central)) return null;
  const { telefono, whatsapp } = conWhatsapp(central);
  return (
    // `tema-portal`: también se muestra en las pantallas de error, fuera del marco del portal. Sin el alto ni el
    // fondo de página que trae el tema.
    <div className={`tema-portal ${e.formulario}`} style={{ minHeight: 0, background: 'none' }} role="group" aria-label="Contactar a la central">
      {telefono && (
        <a href={`tel:${telefono}`} className={claseBoton('secundario', true)}>
          Llamar a la central
        </a>
      )}
      {whatsapp && (
        <a href={enlaceWhatsapp(whatsapp)} target="_blank" rel="noreferrer" className={claseBoton('secundario', true)}>
          WhatsApp de la central
        </a>
      )}
    </div>
  );
}
