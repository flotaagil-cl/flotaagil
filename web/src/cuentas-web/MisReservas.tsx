import { Link } from 'react-router';
import estilos from '../componentes/panel.module.css';
import { useSesion } from '../sesion/SesionProvider';

/** HU-33: vista de la cuenta del pasajero. HU-35 agrega sus reservas, su historial y la cancelación. */
export function MisReservas() {
  const { estado } = useSesion();
  if (estado.fase !== 'autenticada') return null;
  const { usuario } = estado;
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Mis reservas</h1>
        <Link to={`/solicitar/${usuario.empresa.slug}`} className={estilos.boton}>
          Pedir un viaje
        </Link>
      </div>
      <p>Hola, {usuario.nombre}.</p>
    </section>
  );
}
