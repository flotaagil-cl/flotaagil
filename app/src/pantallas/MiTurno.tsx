import { useCallback, useEffect, useRef, useState } from 'react';
import { nombreDelMetodo, type MetodoPago } from '../conductor/ejecucion';
import { fechaYHora, pesos } from '../hora';

export interface ViajeDelTurno {
  id: number;
  finalizado_en: string;
  origen: string;
  destino: string;
  monto: number;
  metodo: MetodoPago;
  cerrado_por_central: boolean;
}

export interface ResumenDelTurno {
  en_turno: boolean;
  inicio: string | null;
  fin: string | null;
  viajes: ViajeDelTurno[];
  totales: { metodo: MetodoPago; viajes: number; monto: number }[];
  total: number;
}

interface Props {
  cargar: () => Promise<ResumenDelTurno>;
  volver: () => void;
}

function periodo({ en_turno, inicio, fin }: ResumenDelTurno): string {
  if (!inicio) return 'Aún no tienes turnos registrados.';
  if (en_turno) return `Turno en curso desde ${fechaYHora(inicio)}.`;
  return `Último turno: ${fechaYHora(inicio)} a ${fin ? fechaYHora(fin) : 'sin registro de término'}.`;
}

/** HU-18: viajes finalizados del turno actual o, fuera de turno, del último, con totales para rendir caja. */
export function MiTurno({ cargar, volver }: Props) {
  const [resumen, setResumen] = useState<ResumenDelTurno | null>(null);
  const [falla, setFalla] = useState(false);
  const ultima = useRef(0);

  const actualizar = useCallback(async () => {
    const numero = ++ultima.current;
    setFalla(false);
    try {
      const datos = await cargar();
      if (numero === ultima.current) setResumen(datos);
    } catch {
      if (numero === ultima.current) setFalla(true);
    }
  }, [cargar]);

  useEffect(() => {
    void actualizar();
    return () => {
      ultima.current += 1; // Una respuesta tardía ya no aplica.
    };
  }, [actualizar]);

  return (
    <main>
      <h1>Mi turno</h1>
      {falla && (
        <p className="error" role="alert">
          No se pudieron cargar tus viajes.
        </p>
      )}
      {!resumen && !falla && <p>Cargando…</p>}
      {resumen && (
        <>
          <p className="secundario">{periodo(resumen)}</p>
          {resumen.inicio && resumen.viajes.length === 0 && <p>Sin viajes completados en este turno.</p>}
          {resumen.viajes.map((viaje) => (
            <div key={viaje.id} className="tarjeta">
              <h2>{fechaYHora(viaje.finalizado_en)}</h2>
              {viaje.cerrado_por_central && <p className="aviso">Cerrado por la central</p>}
              <dl>
                <dt>Origen</dt>
                <dd>{viaje.origen}</dd>
                <dt>Destino</dt>
                <dd>{viaje.destino}</dd>
                <dt>Monto</dt>
                <dd>{pesos(viaje.monto)}</dd>
                <dt>Pago</dt>
                <dd>{nombreDelMetodo(viaje.metodo)}</dd>
              </dl>
            </div>
          ))}
          {resumen.viajes.length > 0 && (
            <div className="tarjeta">
              <h2>Totales por método de pago</h2>
              <dl>
                {resumen.totales.map((total) => (
                  <div key={total.metodo} className="fila-total">
                    <dt>
                      {nombreDelMetodo(total.metodo)} ({total.viajes})
                    </dt>
                    <dd>{pesos(total.monto)}</dd>
                  </div>
                ))}
                <div className="fila-total">
                  <dt>Total</dt>
                  <dd>
                    <strong>{pesos(resumen.total)}</strong>
                  </dd>
                </div>
              </dl>
            </div>
          )}
        </>
      )}
      <div className="acciones">
        <button type="button" onClick={volver}>
          Volver
        </button>
        <button type="button" onClick={() => void actualizar()}>
          Actualizar
        </button>
      </div>
    </main>
  );
}
