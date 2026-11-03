import { useState } from 'react';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import campos from '../../formularios/formularios.module.css';
import { useImportarVehiculos, type Informe } from '../api';
import { Celda } from '../componentes/comunes';
import { erroresDelBackend, mensajeDeError } from '../errores';

const COLUMNAS = { patente: 'Patente', marca_modelo: 'Marca y modelo', anio: 'Año', capacidad: 'Capacidad' } as const;

/** Error del archivo (`archivo` en un 400 sin informe) o mensaje general. */
function fallaDe(error: unknown): string {
  if (error instanceof ErrorApi && error.estado === 400) {
    const { campos: porCampo, generales } = erroresDelBackend(error.cuerpo, ['archivo']);
    return porCampo.archivo ?? generales.join(' ');
  }
  return mensajeDeError(error, 'la página');
}

function esInforme(cuerpo: unknown): cuerpo is Informe {
  return Boolean(cuerpo && typeof cuerpo === 'object' && 'filas' in cuerpo);
}

/**
 * Carga inicial por CSV en dos pasos: «Revisar» valida sin crear y muestra cada línea con sus errores;
 * «Cargar» crea todos o ninguno. Si el archivo cambia, hay que revisarlo de nuevo.
 */
export function ImportarVehiculos() {
  const importar = useImportarVehiculos();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [informe, setInforme] = useState<Informe | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [creados, setCreados] = useState<number | null>(null);

  async function enviar(confirmar: boolean) {
    if (!archivo) return;
    setFalla(null);
    try {
      const resultado = await importar.mutateAsync({ archivo, confirmar });
      setInforme(resultado);
      if (confirmar) setCreados(resultado.creados);
    } catch (error) {
      // Con `confirmar` y errores, el 400 trae el informe actualizado (p. ej. otra persona cargó una patente).
      if (error instanceof ErrorApi && esInforme(error.cuerpo)) {
        setInforme(error.cuerpo);
        setFalla('No se cargó ningún vehículo: hay líneas con errores.');
      } else {
        setFalla(fallaDe(error));
      }
    }
  }

  if (creados !== null) {
    return (
      <section>
        <h1>Cargar vehículos por CSV</h1>
        <Aviso>
          Se {creados === 1 ? 'cargó 1 vehículo' : `cargaron ${creados} vehículos`}.
        </Aviso>
        <div className={estilos.acciones}>
          <Link to="/vehiculos" className={estilos.boton}>
            Ver los vehículos
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Cargar vehículos por CSV</h1>
        <Link to="/vehiculos" className={estilos.botonSecundario}>
          Volver a los vehículos
        </Link>
      </div>
      <div className={estilos.tarjeta}>
        <p>
          La primera línea debe tener los títulos <code>patente</code>, <code>marca_modelo</code>, <code>anio</code> y,
          opcional, <code>capacidad</code> (si falta, 4). Sirve el CSV que guarda Excel (separado por punto y coma) y uno
          separado por comas. Máximo 500 vehículos. Se cargan todos o ninguno.
        </p>
        <pre className={estilos.secundario}>patente;marca_modelo;anio;capacidad{'\n'}AB1234;Toyota Yaris;2022;4</pre>
        <label className={campos.campo}>
          Archivo CSV
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={(evento) => {
              setArchivo(evento.target.files?.[0] ?? null);
              setInforme(null);
              setFalla(null);
            }}
          />
        </label>
        <div className={estilos.acciones}>
          <button type="button" className={estilos.botonSecundario} disabled={!archivo || importar.isPending} onClick={() => void enviar(false)}>
            {importar.isPending && !informe ? 'Revisando…' : 'Revisar'}
          </button>
        </div>
      </div>

      {falla && <Aviso tipo="error">{falla}</Aviso>}

      {informe && (
        <>
          <p className={estilos.resumen} aria-live="polite">
            <span>
              {informe.validas} {informe.validas === 1 ? 'línea válida' : 'líneas válidas'} ·{' '}
              {informe.con_errores} con errores
            </span>
          </p>
          <table className={estilos.tabla} aria-label="Revisión del archivo">
            <thead>
              <tr>
                <th scope="col">Línea</th>
                {Object.values(COLUMNAS).map((titulo) => (
                  <th scope="col" key={titulo}>
                    {titulo}
                  </th>
                ))}
                <th scope="col">Revisión</th>
              </tr>
            </thead>
            <tbody>
              {informe.filas.map((fila) => {
                const errores = Object.entries(fila.errores);
                return (
                  <tr key={fila.linea} data-error={errores.length > 0 || undefined}>
                    <Celda titulo="Línea">{fila.linea}</Celda>
                    {Object.entries(COLUMNAS).map(([clave, titulo]) => (
                      <Celda titulo={titulo} key={clave}>
                        {fila.datos[clave] || '—'}
                      </Celda>
                    ))}
                    <Celda titulo="Revisión">
                      {errores.length ? (
                        <ul className={estilos.erroresFila}>
                          {errores.map(([campo, mensajes]) => (
                            <li key={campo}>
                              {COLUMNAS[campo as keyof typeof COLUMNAS] ?? campo}: {mensajes.join(' ')}
                            </li>
                          ))}
                        </ul>
                      ) : (
                        'Lista'
                      )}
                    </Celda>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {informe.con_errores === 0 ? (
            <div className={estilos.acciones}>
              <button type="button" className={estilos.boton} disabled={importar.isPending} onClick={() => void enviar(true)}>
                {importar.isPending ? 'Cargando…' : `Cargar ${informe.validas} ${informe.validas === 1 ? 'vehículo' : 'vehículos'}`}
              </button>
            </div>
          ) : (
            <p className={estilos.explicacion}>Corrige las líneas con errores en el archivo, elígelo de nuevo y revísalo.</p>
          )}
        </>
      )}
    </section>
  );
}
