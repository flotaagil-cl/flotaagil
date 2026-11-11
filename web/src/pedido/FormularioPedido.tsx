import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { Boton } from '../diseno/Boton';
import { Campo, DatoFijo } from '../diseno/Campo';
import { Contador } from '../diseno/Contador';
import e from '../diseno/diseno.module.css';
import { Segmentado } from '../diseno/Segmentado';
import { Destacado } from '../diseno/Tarjeta';
import { hoy } from '../hora/hora';
import {
  AEROPUERTO,
  armarPedido,
  horaDe,
  recogidaSugerida,
  textoAntelacion,
  VALORES_INICIALES,
  type CuerpoPedido,
  type EmpresaPublica,
  type Errores,
  type TipoPedido,
  type ValoresPedido,
} from './pedido';

interface Props {
  tipo: TipoPedido;
  empresa: EmpresaPublica;
  /** HU-42: al volver de «Revisa tu pedido» (editar o error del servidor) se conservan los datos. */
  iniciales?: ValoresPedido;
  erroresIniciales?: Errores;
  /** HU-42: con los datos válidos se pasa a revisar; el envío ocurre al confirmar. */
  alRevisar: (valores: ValoresPedido, cuerpo: CuerpoPedido) => void;
}

/** HU-39: datos de cada tipo de viaje, con pasajeros y maletas. */
export function FormularioPedido({ tipo, empresa, iniciales, erroresIniciales, alRevisar }: Props) {
  const [v, setV] = useState<ValoresPedido>(iniciales ?? VALORES_INICIALES);
  const [errores, setErrores] = useState<Errores>(erroresIniciales ?? {});
  // La API de vuelos no respondió: el servidor pidió la hora de llegada para no inventarla.
  const pedirHoraLlegada = Boolean(erroresIniciales?.vueloHora || iniciales?.vueloHora);
  const cambiar = <K extends keyof ValoresPedido>(campo: K, valor: ValoresPedido[K]) => setV((actual) => ({ ...actual, [campo]: valor }));
  const texto = (campo: keyof ValoresPedido) => (evento: { target: { value: string } }) => cambiar(campo, evento.target.value as never);
  const maximo = empresa.capacidad_maxima;
  const minimoFecha = hoy();

  function revisar(evento: FormEvent) {
    evento.preventDefault();
    const armado = armarPedido(tipo, v, empresa);
    if ('errores' in armado) {
      setErrores(armado.errores);
      return;
    }
    setErrores({});
    alRevisar(v, armado.cuerpo);
  }

  const contadores = (
    <div className={e.filaContadores}>
      <Contador etiqueta="Pasajeros" unidad="un pasajero" valor={v.pasajeros} min={1} max={maximo} onCambiar={(n) => cambiar('pasajeros', n)} error={errores.pasajeros} />
      <Contador etiqueta="Maletas" unidad="una maleta" valor={v.maletas} min={0} max={20} onCambiar={(n) => cambiar('maletas', n)} error={errores.maletas} />
    </div>
  );

  const sugerida = recogidaSugerida(v, empresa);
  const antelacion = v.salidaTipo === 'INTERNACIONAL' ? empresa.antelacion_vuelo_internacional_min : empresa.antelacion_vuelo_nacional_min;

  return (
    <form className={e.formulario} onSubmit={revisar} noValidate aria-label="Datos del traslado">
      {errores.general && (
        <p className={e.alerta} role="alert">
          {errores.general}
        </p>
      )}

      {tipo === 'desde-aeropuerto' && (
        <>
          <DatoFijo etiqueta="Origen" valor={AEROPUERTO} />
          <div className={e.fila}>
            <Campo etiqueta="Número de vuelo" placeholder="LA 845" autoCapitalize="characters" value={v.vueloNumero} onChange={texto('vueloNumero')} error={errores.vueloNumero} />
            <Campo etiqueta="Fecha" type="date" min={minimoFecha} value={v.vueloFecha} onChange={texto('vueloFecha')} error={errores.vueloFecha} />
          </div>
          {pedirHoraLlegada && (
            <Campo etiqueta="Hora de llegada" type="time" value={v.vueloHora} onChange={texto('vueloHora')} error={errores.vueloHora} />
          )}
          <Destacado titulo="Seguimos tu vuelo por ti">Si se atrasa, tu conductor ya lo sabe. No tienes que avisarnos.</Destacado>
          <Campo etiqueta="¿A dónde vas?" placeholder="Dirección de destino" autoComplete="street-address" value={v.destino} onChange={texto('destino')} error={errores.destino} />
          {contadores}
        </>
      )}

      {tipo === 'al-aeropuerto' && (
        <>
          <Campo etiqueta="¿Dónde te recogemos?" placeholder="Dirección de recogida" autoComplete="street-address" value={v.origen} onChange={texto('origen')} error={errores.origen} />
          <DatoFijo etiqueta="Destino" valor={AEROPUERTO} />
          <div className={e.fila}>
            <Campo etiqueta="Fecha del vuelo" type="date" min={minimoFecha} value={v.salidaFecha} onChange={texto('salidaFecha')} error={errores.salidaFecha} />
            <Campo etiqueta="Hora de salida" type="time" value={v.salidaHora} onChange={texto('salidaHora')} error={errores.salidaHora} />
          </div>
          <Segmentado
            etiqueta="Tipo de vuelo"
            valor={v.salidaTipo}
            onCambiar={(tipoVuelo) => cambiar('salidaTipo', tipoVuelo)}
            opciones={[
              { valor: 'NACIONAL', texto: 'Nacional' },
              { valor: 'INTERNACIONAL', texto: 'Internacional' },
            ]}
          />
          {sugerida !== null && !v.cambiarRecogida && (
            <Destacado
              titulo={`Te recogemos a las ${horaDe(sugerida)}`}
              icono="reloj"
              accion={
                <button type="button" className={e.destacadoAccion} onClick={() => cambiar('cambiarRecogida', true)}>
                  Cambiar
                </button>
              }
            >
              {textoAntelacion(antelacion)} antes de tu vuelo {v.salidaTipo === 'INTERNACIONAL' ? 'internacional' : 'nacional'}.
            </Destacado>
          )}
          {v.cambiarRecogida && (
            <div className={e.fila}>
              <Campo etiqueta="Fecha de recogida" type="date" min={minimoFecha} value={v.recogidaFecha} onChange={texto('recogidaFecha')} />
              <Campo etiqueta="Hora de recogida" type="time" value={v.recogidaHora} onChange={texto('recogidaHora')} error={errores.recogidaHora} />
            </div>
          )}
          {!v.cambiarRecogida && errores.recogidaHora && (
            <p className={e.alerta} role="alert">
              {errores.recogidaHora} Cambia la hora de recogida.
            </p>
          )}
          {contadores}
        </>
      )}

      {tipo === 'en-la-ciudad' && (
        <>
          <Campo etiqueta="Origen" placeholder="¿Dónde te recogemos?" autoComplete="street-address" value={v.origen} onChange={texto('origen')} error={errores.origen} />
          <Campo etiqueta="Destino" placeholder="¿A dónde vas?" value={v.destino} onChange={texto('destino')} error={errores.destino} />
          <Segmentado
            etiqueta="¿Cuándo?"
            forma="pastillas"
            valor={v.ahora ? 'ahora' : 'programar'}
            onCambiar={(cuando) => cambiar('ahora', cuando === 'ahora')}
            opciones={[
              { valor: 'ahora', texto: 'Lo antes posible' },
              { valor: 'programar', texto: 'Programar' },
            ]}
          />
          {v.ahora ? (
            <p className={e.saludo}>Te recogemos en unos {empresa.anticipacion_minima_min} minutos.</p>
          ) : (
            <div className={e.fila}>
              <Campo etiqueta="Fecha" type="date" min={minimoFecha} value={v.recogidaFecha} onChange={texto('recogidaFecha')} />
              <Campo etiqueta="Hora" type="time" value={v.recogidaHora} onChange={texto('recogidaHora')} error={errores.recogidaHora} />
            </div>
          )}
          {contadores}
        </>
      )}

      <Boton type="submit" ancho>
        Pedir mi traslado
      </Boton>
      <p className={e.nota}>
        Te avisaremos de tu viaje por WhatsApp. Tus datos se tratan según el{' '}
        <Link to={`/solicitar/${empresa.slug}/privacidad`}>aviso de privacidad</Link> que aceptaste al crear tu cuenta.
      </p>
    </form>
  );
}
