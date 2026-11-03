import { useNavigate } from 'react-router';
import { useCrearVehiculo } from '../api';
import { FormularioVehiculo } from '../componentes/FormularioVehiculo';
import { cuerpoCrearVehiculo, VEHICULO_VACIO } from '../formularios';

export function VehiculoNuevo() {
  const crear = useCrearVehiculo();
  const navegar = useNavigate();
  return (
    <section>
      <h1>Nuevo vehículo</h1>
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
