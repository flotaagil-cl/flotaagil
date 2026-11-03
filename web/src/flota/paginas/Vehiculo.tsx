import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { useIdDeRuta } from '../../rutas/idDeRuta';
import { useEditarVehiculo, useVehiculo, type Vehiculo as TipoVehiculo } from '../api';
import { FallaDeCarga, NoEncontrado } from '../componentes/comunes';
import { FormularioVehiculo } from '../componentes/FormularioVehiculo';
import { mensajeDeError } from '../errores';
import { cuerpoEditarVehiculo, type DatosVehiculo } from '../formularios';

export function Vehiculo() {
  const id = useIdDeRuta();
  if (id === null) return <NoEncontrado que="el vehículo" volverA="/vehiculos" texto="Volver a los vehículos" />;
  return <VehiculoDe id={id} />;
}

function VehiculoDe({ id }: { id: number }) {
  const consulta = useVehiculo(id);
  if (consulta.isPending) return <Cargando />;
  if (consulta.isError) {
    if (consulta.error instanceof ErrorApi && consulta.error.estado === 404) {
      return <NoEncontrado que="el vehículo" volverA="/vehiculos" texto="Volver a los vehículos" />;
    }
    return <FallaDeCarga error={consulta.error} que="el vehículo" reintentar={() => void consulta.refetch()} />;
  }
  return <Ficha vehiculo={consulta.data} />;
}

function datosDe(vehiculo: TipoVehiculo): DatosVehiculo {
  return {
    patente: vehiculo.patente,
    marca_modelo: vehiculo.marca_modelo,
    anio: vehiculo.anio,
    capacidad: vehiculo.capacidad ?? 4,
  };
}

function Ficha({ vehiculo }: { vehiculo: TipoVehiculo }) {
  const editar = useEditarVehiculo(vehiculo.id);
  const ubicacion = useLocation();
  const [aviso, setAviso] = useState<string | null>((ubicacion.state as { aviso?: string } | null)?.aviso ?? null);
  const [falla, setFalla] = useState<string | null>(null);
  // Los valores del formulario se toman una vez, para que un guardado no reinicie lo escrito.
  const [antes, setAntes] = useState(() => datosDe(vehiculo));

  async function cambiarActivo() {
    setAviso(null);
    setFalla(null);
    try {
      const nuevo = await editar.mutateAsync({ activo: !vehiculo.activo });
      setAviso(nuevo.activo ? 'Vehículo activado.' : 'Vehículo desactivado.');
    } catch (error) {
      setFalla(mensajeDeError(error, 'el vehículo'));
    }
  }

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>
          Vehículo {vehiculo.patente}{' '}
          <span className={`${estilos.etiqueta} ${vehiculo.activo ? estilos.curso : estilos.cancelado}`}>
            {vehiculo.activo ? 'Activo' : 'Inactivo'}
          </span>
        </h1>
        <Link to="/vehiculos" className={estilos.botonSecundario}>
          Volver a los vehículos
        </Link>
      </div>
      {aviso && <Aviso>{aviso}</Aviso>}
      {falla && <Aviso tipo="error">{falla}</Aviso>}

      <div className={estilos.tarjeta}>
        <h2>Conductores asociados</h2>
        {vehiculo.conductores.length ? (
          <ul>
            {vehiculo.conductores.map((conductor) => (
              <li key={conductor.id}>
                <Link to={`/conductores/${conductor.id}`}>{conductor.nombre}</Link>
              </li>
            ))}
          </ul>
        ) : (
          <p>Ninguno. Se asocian desde la ficha de cada conductor.</p>
        )}
        <div className={estilos.acciones}>
          <button
            type="button"
            className={vehiculo.activo ? estilos.botonPeligro : estilos.boton}
            disabled={editar.isPending}
            onClick={() => void cambiarActivo()}
          >
            {vehiculo.activo ? 'Desactivar' : 'Activar'}
          </button>
        </div>
        <p className={estilos.explicacion}>
          {vehiculo.activo
            ? 'Un vehículo inactivo no se puede declarar para un turno. No se desactiva si un conductor lo tiene declarado en turno o tiene un viaje en curso.'
            : 'Inactivo: no se puede declarar para un turno ni asociar a un conductor.'}
        </p>
      </div>

      <FormularioVehiculo
        key={JSON.stringify(antes)}
        modo="editar"
        iniciales={{ ...antes, anio: String(antes.anio), capacidad: String(antes.capacidad) }}
        volverA="/vehiculos"
        enviar={async (datos) => {
          setAviso(null);
          setFalla(null);
          const cambios = cuerpoEditarVehiculo(datos, antes);
          if (Object.keys(cambios).length === 0) {
            setAviso('No hay cambios que guardar.');
            return;
          }
          const nuevo = await editar.mutateAsync(cambios);
          setAntes(datosDe(nuevo));
          setAviso('Cambios guardados.');
        }}
      />
    </section>
  );
}
