import { ImportarCsv } from '../componentes/ImportarCsv';

const COLUMNAS = {
  nombre: 'Nombre',
  email: 'Correo',
  rut: 'RUT',
  telefono: 'Teléfono',
  licencia_clase: 'Licencia',
  licencia_vence: 'Vence',
};

export function ImportarConductores() {
  return (
    <ImportarCsv
      titulo="Cargar conductores por CSV"
      ruta="/api/conductores/importar/"
      volverA="/conductores"
      textoVolver="Volver a los conductores"
      columnas={COLUMNAS}
      singular="conductor"
      plural="conductores"
      ejemplo={'nombre;email;rut;telefono;licencia_clase;licencia_vence\nRosa Pérez;rosa@correo.example;12.345.678-5;912345678;A2;31-12-2027'}
      ayuda={
        <>
          <p>
            La primera línea debe tener <code>nombre</code>, <code>email</code>, <code>rut</code>, <code>telefono</code>,{' '}
            <code>licencia_clase</code> (A1, A2 o A3) y <code>licencia_vence</code> (DD-MM-AAAA o AAAA-MM-DD). Sirve el CSV
            que guarda Excel. Máximo 500 conductores. Se cargan todos o ninguno.
          </p>
          <p>
            El archivo no lleva contraseñas: las cuentas quedan sin acceso hasta que generes la contraseña temporal de cada
            conductor desde su ficha.
          </p>
        </>
      }
    />
  );
}
