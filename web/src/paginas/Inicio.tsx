import { Link } from 'react-router';
import { hoy } from '../hora/hora';
import { useSesion } from '../sesion/SesionProvider';
import { Indicadores } from './Indicadores';
import estilos from './Inicio.module.css';

/** Indicadores del día (HU-01) y atajos al listado filtrado. */
export function Inicio() {
  const { estado } = useSesion();
  if (estado.fase !== 'autenticada') return null;
  const atajos = [
    { a: `/reservas?fecha=${hoy()}`, titulo: 'Reservas de hoy', texto: 'Recogidas del día (hora de Santiago).' },
    { a: '/reservas?estado=PENDIENTE_CONFIRMACION', titulo: 'Por confirmar', texto: 'Esperan la respuesta del pasajero por WhatsApp.' },
    { a: '/reservas?estado=SOLICITADO', titulo: 'Sin asignar', texto: 'Solicitadas, todavía sin conductor.' },
    { a: '/reservas', titulo: 'Próximas', texto: 'Todas desde hoy 00:00.' },
  ];
  return (
    <section>
      <h1>Inicio</h1>
      <p>Hola, {estado.usuario.nombre}.</p>
      <p>Panel de {estado.usuario.empresa.razon_social}.</p>
      <Indicadores />
      <ul className={estilos.atajos} aria-label="Atajos a las reservas">
        {atajos.map((atajo) => (
          <li key={atajo.a}>
            <Link to={atajo.a}>
              <strong>{atajo.titulo}</strong>
              <span>{atajo.texto}</span>
            </Link>
          </li>
        ))}
      </ul>
      <Link to="/reservas/nueva" className={estilos.boton}>
        Nueva reserva
      </Link>
    </section>
  );
}
