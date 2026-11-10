import estilos from '../componentes/panel.module.css';
import { useSesion } from '../sesion/SesionProvider';

/** HU-33: vista de la cuenta de la empresa con convenio. HU-34 agrega el estado, la reserva y sus reservas. */
export function MiConvenio() {
  const { estado } = useSesion();
  if (estado.fase !== 'autenticada') return null;
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Mi convenio</h1>
      </div>
      <p>
        Hola, {estado.usuario.nombre}. Tu cuenta está asociada a {estado.usuario.empresa.razon_social}.
      </p>
    </section>
  );
}
