import { Link, useNavigate } from 'react-router';
import estilos from '../../componentes/panel.module.css';
import { Icono } from '../../diseno/Icono';
import { useCrearVehiculo } from '../api';
import { FormularioVehiculo } from '../componentes/FormularioVehiculo';
import s from '../flota.module.css';
import { cuerpoCrearVehiculo, VEHICULO_VACIO } from '../formularios';

export function VehiculoNuevo() {
  const crear = useCrearVehiculo();
  const navegar = useNavigate();
  return (
    <section>
      <div className={s.encabezado}>
        <div className={s.tituloBloque}>
          <h1>Nuevo vehículo</h1>
          <p className={s.subtitulo}>Registra una patente habilitada para declararse en turno y asignar viajes.</p>
        </div>
        <div className={s.accionesEncabezado}>
          <Link to="/vehiculos" className={`${estilos.botonSecundario} ${s.botonConIcono}`}>
            <Icono nombre="atras" tamano={16} />
            Volver a los vehículos
          </Link>
        </div>
      </div>
      <FormularioVehiculo
        modo="crear"
        iniciales={VEHICULO_VACIO}
        volverA="/vehiculos"
        enviar={async (datos) => {
          const vehiculo = await crear.mutateAsync(cuerpoCrearVehiculo(datos));
          navegar(`/vehiculos/${vehiculo.id}`, { replace: true, state: { aviso: 'Vehículo registrado.' } });
        }}
      />
    </section>
  );
}
