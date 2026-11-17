import { useEffect } from 'react';
import { Link } from 'react-router';
import { claseBoton } from '../../diseno/clases';
import e from '../../diseno/diseno.module.css';
import { useContextoPortal } from '../contexto';
import { ReservaPublica } from './ReservaPublica';

/**
 * La dirección que la empresa comparte (/solicitar/:slug). Sin el módulo de cuentas (DC-51) es la reserva pública
 * (HU-51). Con el módulo ofrece las dos opciones (HU-60): ingresar con la cuenta o reservar sin cuenta.
 */
export function IrAlIngreso() {
  const { empresa, slug } = useContextoPortal();

  useEffect(() => {
    if (empresa.modulo_cuentas) document.title = `Pide tu traslado · ${empresa.razon_social}`;
  }, [empresa.modulo_cuentas, empresa.razon_social]);

  if (!empresa.modulo_cuentas) return <ReservaPublica />;
  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-opciones">
      <h1 id="titulo-opciones" className={e.tituloPagina}>
        Pide tu traslado
      </h1>
      <p className={e.subtituloPagina}>Con tu cuenta ves tus viajes y pides más rápido. También puedes reservar sin cuenta y confirmar por correo.</p>
      <div className={e.formulario}>
        <Link to={`/solicitar/${slug}/ingresar`} className={claseBoton('principal')}>
          Ingresar
        </Link>
        <Link to={`/solicitar/${slug}/reservar`} className={claseBoton('secundario')}>
          Reservar sin cuenta
        </Link>
      </div>
    </section>
  );
}
