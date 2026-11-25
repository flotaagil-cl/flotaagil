import { Link } from 'react-router';
import { useTitulo } from '../../diseno/titulo';
import { useContextoPortal } from '../contexto';
import { TextoPrivacidad } from '../Privacidad';
import estilos from '../portal.module.css';

export function Privacidad() {
  const { empresa, slug } = useContextoPortal();
  useTitulo('Aviso de privacidad', empresa.razon_social);
  return (
    <section className={estilos.tarjeta}>
      <h1>Aviso de privacidad</h1>
      <TextoPrivacidad razonSocial={empresa.razon_social} />
      {/* HU-40: ya no hay formulario de invitado; se vuelve al ingreso de la empresa. */}
      <Link to={`/solicitar/${slug}/ingresar`} className={estilos.botonSecundario}>
        Volver al ingreso
      </Link>
    </section>
  );
}
