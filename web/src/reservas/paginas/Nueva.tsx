import { Link, useNavigate } from 'react-router';
import { useCrearViaje } from '../api';
import { FormularioReserva } from '../componentes/FormularioReserva';
import { mensajeDeErrorApi, sinRespuesta } from '../errores';
import { cuerpoCrear, VALORES_NUEVA } from '../formulario';
import estilos from '../../componentes/panel.module.css';
import s from '../componentes/FormularioReserva.module.css';

export function Nueva() {
  const crear = useCrearViaje();
  const navegar = useNavigate();
  return (
    <section>
      <div className={s.cabecera}>
        <h1>Nueva reserva</h1>
        <Link to="/reservas" className={estilos.botonSecundario}>
          Volver a las reservas
        </Link>
      </div>
      <FormularioReserva
        modo="crear"
        iniciales={VALORES_NUEVA}
        volverA="/reservas"
        enviar={async (valores) => {
          const viaje = await crear.mutateAsync(cuerpoCrear(valores));
          navegar(`/reservas/${viaje.id}`, { replace: true });
        }}
        describirFalla={(error) =>
          // El POST no es idempotente: sin respuesta no se sabe si la reserva quedó creada.
          sinRespuesta(error) ? (
            <>
              No sabemos si la reserva se creó: revisa el <Link to="/reservas">listado</Link> antes de reintentar.
            </>
          ) : (
            mensajeDeErrorApi(error)
          )
        }
      />
    </section>
  );
}
