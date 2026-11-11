import { Link } from 'react-router';
import { useContextoPortal } from '../contexto';
import { TextoPrivacidad } from '../Privacidad';
import estilos from '../portal.module.css';

export function Privacidad() {
  const { empresa, slug } = useContextoPortal();
  return (
    <section className={estilos.tarjeta}>
      <h1>Aviso de privacidad</h1>
      <TextoPrivacidad razonSocial={empresa.razon_social} />
      {/* HU-40: ya no hay formulario de invitado; se vuelve al ingreso de la empresa. */}
      <Link to={`/login?empresa=${slug}`} className={estilos.botonSecundario}>
        Volver al ingreso
      </Link>
    </section>
  );
}
