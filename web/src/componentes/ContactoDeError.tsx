import { useLocation } from 'react-router';
import { useEntorno } from '../entornoContexto';
import { esRutaDelPortal, leerCentral, slugDeRuta } from './central';
import { BotonesCentral } from './BotonesCentral';

/**
 * HU-49 (DC-80): en el portal y en las cuentas web, una pantalla de error ofrece llamar o escribir a la central
 * con los números guardados la última vez que cargó la empresa (el servidor puede estar caído). En el panel, nada.
 */
export function ContactoDeError() {
  const { pathname } = useLocation();
  const { almacen } = useEntorno();
  if (!esRutaDelPortal(pathname)) return null;
  const central = leerCentral(almacen, slugDeRuta(pathname));
  if (!central) return null;
  return (
    <>
      <p>Si necesitas tu traslado ahora, contacta a la central:</p>
      <BotonesCentral central={central} />
    </>
  );
}
