import { useState, type FormEvent } from 'react';
import { Icono } from '../componentes/Icono';
import { leerMonto, metodosDePago, pasoSiguiente, type Accion, type MetodoPago } from '../conductor/ejecucion';
import type { ViajeActivo } from '../navegacion';

export interface Pago {
  metodo: MetodoPago;
  monto: number;
}

interface Props {
  viaje: ViajeActivo;
  /** Registra el paso; resuelve con el mensaje de error, o null si quedó registrado. */
  avanzar: (accion: Accion | 'finalizar', pago?: Pago) => Promise<string | null>;
}

/** Botón del paso siguiente y, con el pasajero a bordo, el pago obligatorio para finalizar (HU-16, RN-10). */
export function AvanceViaje({ viaje, avanzar }: Props) {
  const metodos = metodosDePago(viaje.convenio);
  const [metodo, setMetodo] = useState<MetodoPago>(metodos[0].valor);
  const [monto, setMonto] = useState(viaje.tarifa === null ? '' : String(viaje.tarifa));
  const [errorMonto, setErrorMonto] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const paso = pasoSiguiente(viaje.estado);

  async function enviar(accion: Accion | 'finalizar', pago?: Pago) {
    setEnviando(true);
    setFalla(null);
    const error = await avanzar(accion, pago);
    if (error) setFalla(error);
    setEnviando(false);
  }

  function finalizar(evento: FormEvent) {
    evento.preventDefault();
    const leido = leerMonto(monto);
    setErrorMonto(leido.error ?? null);
    if (leido.monto !== undefined) void enviar('finalizar', { metodo, monto: leido.monto });
  }

  const aviso = falla && (
    <p className="error alerta-bloque" role="alert">
      <Icono nombre="alerta" tamano={18} />
      <span>{falla}</span>
    </p>
  );

  if (paso) {
    return (
      <div className="avance">
        {viaje.estado === 'EN_CAMINO' && (
          <p className="secundario">La llegada se marca sola a 150 m del punto de recogida.</p>
        )}
        {viaje.estado === 'EN_ZONA' && (
          <p className="aviso alerta-bloque alerta-compacta">
            <Icono nombre="ubicacion" tamano={18} />
            <span>Llegaste al punto de recogida.</span>
          </p>
        )}
        {aviso}
        <button className="principal" type="button" disabled={enviando} onClick={() => void enviar(paso.accion)}>
          {enviando ? paso.enviando : paso.texto}
        </button>
      </div>
    );
  }

  return (
    <form className="avance" onSubmit={finalizar} noValidate>
      <div className="login-campo">
        <span id="metodo-pago-titulo" className="etiqueta-campo">
          Método de pago
        </span>
        <div className="metodos-pago" role="radiogroup" aria-labelledby="metodo-pago-titulo">
          {metodos.map((opcion) => (
            <button
              key={opcion.valor}
              type="button"
              role="radio"
              aria-checked={metodo === opcion.valor}
              className={metodo === opcion.valor ? 'metodo-opcion activo' : 'metodo-opcion'}
              onClick={() => setMetodo(opcion.valor)}
            >
              {opcion.texto}
            </button>
          ))}
        </div>
      </div>

      <div className="login-campo">
        <label htmlFor="monto">Monto cobrado (CLP)</label>
        <div className={errorMonto ? 'campo-entrada campo-entrada-error' : 'campo-entrada'}>
          <span className="campo-prefijo" aria-hidden="true">
            $
          </span>
          <input
            id="monto"
            inputMode="numeric"
            autoComplete="off"
            placeholder="0"
            value={monto}
            aria-invalid={errorMonto !== null}
            aria-describedby={errorMonto ? 'monto-error' : undefined}
            onChange={(e) => {
              setMonto(e.target.value);
              setErrorMonto(null);
            }}
          />
        </div>
        {errorMonto && (
          <p className="error alerta-bloque alerta-compacta" id="monto-error" role="alert">
            <Icono nombre="alerta" tamano={16} />
            <span>{errorMonto}</span>
          </p>
        )}
      </div>

      {aviso}
      <button className="principal" type="submit" disabled={enviando}>
        {enviando ? 'Finalizando…' : 'Finalizar viaje'}
      </button>
    </form>
  );
}
