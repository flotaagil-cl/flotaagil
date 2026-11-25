import { useCallback, useEffect, useRef, useState } from 'react';
import { useAtras } from '../atras';
import { DeslizarParaActualizar } from '../componentes/DeslizarParaActualizar';
import { Icono } from '../componentes/Icono';
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

  useAtras(volver);

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
    <DeslizarParaActualizar alActualizar={actualizar}>
      <main className="app-pantalla">
        <header className="app-barra">
          <button type="button" className="barra-atras" aria-label="Volver" onClick={volver}>
            <Icono nombre="atras" tamano={22} />
          </button>
          <div className="barra-titulos">
            <h1>Mi turno</h1>
            <p className="barra-subtitulo">Resumen y viajes completados</p>
          </div>
          {resumen?.inicio && (
            <span className="barra-estado" data-estado={resumen.en_turno ? 'DISPONIBLE' : 'NO_DISPONIBLE'}>
              <Icono nombre={resumen.en_turno ? 'check' : 'reloj'} tamano={14} />
              {resumen.en_turno ? 'En curso' : 'Finalizado'}
            </span>
          )}
        </header>

        <div className="app-cuerpo">
          {falla && (
            <p className="error alerta-bloque" role="alert">
              <Icono nombre="alerta" tamano={18} />
              <span>No se pudieron cargar tus viajes.</span>
            </p>
          )}
          {!resumen && !falla && (
            <div className="tarjeta estado-vacio">
              <p className="secundario">Cargando…</p>
            </div>
          )}
          {resumen && (
            <>
              <div className={resumen.en_turno ? 'tarjeta turno-resumen' : 'tarjeta'}>
                <p className="turno-periodo">{periodo(resumen)}</p>
                {resumen.viajes.length > 0 && (
                  <p className="turno-cantidad">
                    {resumen.viajes.length === 1 ? '1 viaje completado' : `${resumen.viajes.length} viajes completados`}
                  </p>
                )}
              </div>

              {resumen.inicio && resumen.viajes.length === 0 && (
                <div className="tarjeta estado-vacio">
                  <span className="estado-vacio-icono" aria-hidden="true">
                    <Icono nombre="caja" tamano={24} />
                  </span>
                  <p className="estado-vacio-titulo">Sin viajes completados en este turno.</p>
                  <p className="secundario">Cuando finalices un viaje aparecerá aquí con su monto y método de pago.</p>
                </div>
              )}

              {resumen.viajes.map((viaje) => (
                <div key={viaje.id} className="tarjeta viaje-turno">
                  <h2>{fechaYHora(viaje.finalizado_en)}</h2>
                  {viaje.cerrado_por_central && (
                    <p className="aviso alerta-bloque alerta-compacta">
                      <Icono nombre="alerta" tamano={16} />
                      <span>Cerrado por la central</span>
                    </p>
                  )}
                  <dl className="lista-datos">
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
                <div className="tarjeta totales-turno">
                  <h2>Totales por método de pago</h2>
                  <dl className="lista-datos">
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
        </div>
      </main>
    </DeslizarParaActualizar>
  );
}
