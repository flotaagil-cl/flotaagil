import { useState, type ReactNode } from 'react';
import { Link } from 'react-router';
import { ErrorApi } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import campos from '../../formularios/formularios.module.css';
import { useImportar, type Informe, type RutaImportar } from '../api';
import { Celda } from './comunes';
import { erroresDelBackend, mensajeDeError } from '../errores';


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

interface Props {
  titulo: string;
  ruta: RutaImportar;
  volverA: string;
  textoVolver: string;
  /** Columna del informe → título. */
  columnas: Record<string, string>;
  ayuda: ReactNode;
  ejemplo: string;
  singular: string;
  plural: string;
}

/**
 * Carga inicial por CSV en dos pasos: «Revisar» valida sin crear y muestra cada línea con sus errores;
 * «Cargar» crea todos o ninguno. Si el archivo cambia, hay que revisarlo de nuevo.
 */
export function ImportarCsv({ titulo, ruta, volverA, textoVolver, columnas: COLUMNAS, ayuda, ejemplo, singular, plural }: Props) {
  const importar = useImportar(ruta);
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
        setFalla(`No se cargó ningún ${singular}: hay líneas con errores.`);
      } else {
        setFalla(fallaDe(error));
      }
    }
  }

  if (creados !== null) {
    return (
      <section>
        <h1>{titulo}</h1>
        <Aviso>{creados === 1 ? `Se cargó 1 ${singular}.` : `Se cargaron ${creados} ${plural}.`}</Aviso>
        <div className={estilos.acciones}>
          <Link to={volverA} className={estilos.boton}>
            Ver los {plural}
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>{titulo}</h1>
        <Link to={volverA} className={estilos.botonSecundario}>
          {textoVolver}
        </Link>
      </div>
      <div className={estilos.tarjeta}>
        {ayuda}
        <pre className={estilos.secundario}>{ejemplo}</pre>
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
                {importar.isPending ? 'Cargando…' : `Cargar ${informe.validas} ${informe.validas === 1 ? singular : plural}`}
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
