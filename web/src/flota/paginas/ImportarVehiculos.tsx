import { ImportarCsv } from '../componentes/ImportarCsv';

const COLUMNAS = { patente: 'Patente', marca_modelo: 'Marca y modelo', anio: 'Año', capacidad: 'Capacidad' };

export function ImportarVehiculos() {
  return (
    <ImportarCsv
      titulo="Cargar vehículos por CSV"
      ruta="/api/vehiculos/importar/"
      volverA="/vehiculos"
      textoVolver="Volver a los vehículos"
      columnas={COLUMNAS}
      singular="vehículo"
      plural="vehículos"
      ejemplo={'patente;marca_modelo;anio;capacidad\nAB1234;Toyota Yaris;2022;4'}
      ayuda={
        <p>
          La primera línea debe tener los títulos <code>patente</code>, <code>marca_modelo</code>, <code>anio</code> y,
          opcional, <code>capacidad</code> (si falta, 4). Sirve el CSV que guarda Excel (separado por punto y coma) y uno
          separado por comas. Máximo 500 vehículos. Se cargan todos o ninguno.
        </p>
      }
    />
  );
}
