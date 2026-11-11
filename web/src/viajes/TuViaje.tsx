import { useQuery } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Link, Navigate, useParams } from 'react-router';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { iniciales } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import { LineaDeTiempo } from '../diseno/LineaDeTiempo';
import { Mapa } from '../diseno/mapa/Mapa';
import type { Marcador } from '../diseno/mapa/tipos';
import { PantallaConMapa } from '../diseno/PantallaConMapa';
import { Avatar, Insignia, Tarjeta } from '../diseno/Tarjeta';
import { formatearFechaHora } from '../hora/hora';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { MarcoPasajero } from './MarcoPasajero';
import { INSIGNIA, INSIGNIA_VUELO, pasosDelViaje, textoDeCancelacion, TIPO_DE_VIAJE, type TuViaje as Viaje } from './viaje';

/** Cada cuánto se actualiza el estado mientras la pantalla está abierta. */
export const ACTUALIZAR_MS = 20_000;

function marcadores(viaje: Viaje): Marcador[] {
  return [
    { id: 'origen', punto: viaje.origen, tipo: viaje.sentido === 'DESDE_AEROPUERTO' ? 'aeropuerto' : 'origen', etiqueta: viaje.origen_dir },
    { id: 'destino', punto: viaje.destino, tipo: viaje.sentido === 'HACIA_AEROPUERTO' ? 'aeropuerto' : 'destino', etiqueta: viaje.destino_dir },
  ];
}

/**
 * HU-43: «Tu viaje». Estado, conductor, vehículo y patente (desde que el conductor acepta), vuelo y avance, con
 * el mapa de respaldo. Solo el viaje del pasajero (el servidor responde 404 si no es suyo).
 */
export function TuViaje() {
  const { id = '' } = useParams();
  const { estado } = useSesion();
  const api = useApi();
  const numero = Number(id);
  const viaje = useQuery({
    queryKey: ['mi-cuenta', 'viaje', numero],
    queryFn: () => resultado(api.GET('/api/mi-cuenta/reservas/{id}/', { params: { path: { id: numero } } })),
    enabled: Number.isInteger(numero) && numero > 0,
    refetchInterval: ACTUALIZAR_MS,
    retry: false,
  });

  useEffect(() => {
    document.title = 'Tu viaje';
  }, []);

  if (estado.fase !== 'autenticada') return null;
  if (estado.usuario.rol !== 'PASAJERO') return <Navigate to={inicioDeRol(estado.usuario.rol)} replace />;

  let panel;
  if (!Number.isInteger(numero) || numero <= 0 || (viaje.isError && viaje.error instanceof ErrorApi && viaje.error.estado === 404)) {
    panel = (
      <div className={e.formulario}>
        <h1 className={e.tituloPagina}>No encontramos este viaje</h1>
        <p className={e.subtituloPagina}>Revisa el enlace o busca el viaje en tu lista.</p>
        <Link to="/mis-viajes" className={e.enlace}>
          Ver mis viajes
        </Link>
      </div>
    );
  } else if (viaje.isError) {
    panel = <Aviso tipo="error">No pudimos cargar tu viaje. Recarga la página.</Aviso>;
  } else if (!viaje.data) {
    panel = <Cargando />;
  } else {
    const v = viaje.data;
    const insignia = INSIGNIA[v.estado ?? 'SOLICITADO'];
    const cancelacion = textoDeCancelacion(v);
    panel = (
      <div className={e.formulario}>
        <div>
          <div className={e.tituloConInsignia}>
            <h1 className={e.tituloPagina}>Tu viaje</h1>
            <Insignia tono={insignia.tono}>{insignia.texto}</Insignia>
          </div>
          <p className={e.subtituloPagina}>
            Reserva {v.id} · {TIPO_DE_VIAJE[v.sentido ?? 'URBANO']} · {formatearFechaHora(v.recogida_en)}
          </p>
        </div>

        {v.estado === 'CANCELADO' ? (
          <p className={e.alerta} role="status">
            Este viaje fue cancelado.
          </p>
        ) : v.conductor && v.vehiculo ? (
          <Tarjeta como="section" aria-labelledby="titulo-conductor">
            <div className={e.conductor}>
              <Avatar texto={iniciales(v.conductor.nombre)} />
              <div className={e.conductorTexto}>
                <h2 id="titulo-conductor" className={e.conductorNombre}>
                  {v.conductor.nombre}
                </h2>
                <span className={e.conductorAuto}>{v.vehiculo.marca_modelo}</span>
              </div>
              <span className={e.patente} aria-label={`Patente ${v.vehiculo.patente}`}>
                {v.vehiculo.patente}
              </span>
            </div>
            <p className={e.avisoSuave}>
              <Icono nombre="mensaje" tamano={18} />
              <span>Te avisaremos por WhatsApp cuando llegue.</span>
            </p>
          </Tarjeta>
        ) : (
          <Tarjeta como="section" aria-labelledby="titulo-buscando">
            <h2 id="titulo-buscando" className={e.conductorNombre}>
              Estamos buscando tu conductor
            </h2>
            <p className={e.saludo}>Cuando acepte el viaje verás su nombre, el vehículo y la patente aquí y por WhatsApp.</p>
          </Tarjeta>
        )}

        {v.vuelo && (
          <Tarjeta como="section" aria-labelledby="titulo-vuelo">
            <div className={e.heroVueloFila}>
              <h2 id="titulo-vuelo" className={e.heroVueloNumero}>
                Vuelo {v.vuelo.numero}
              </h2>
              {INSIGNIA_VUELO[v.vuelo.estado_vuelo] && (
                <Insignia tono={INSIGNIA_VUELO[v.vuelo.estado_vuelo].tono}>{INSIGNIA_VUELO[v.vuelo.estado_vuelo].texto}</Insignia>
              )}
            </div>
            <p className={e.saludo}>
              Llega {formatearFechaHora(v.vuelo.hora_estimada ?? v.vuelo.hora_programada)} · tu conductor ya está avisado
            </p>
          </Tarjeta>
        )}

        {v.estado !== 'CANCELADO' && (
          <Tarjeta>
            <LineaDeTiempo etiqueta="Avance de tu viaje" pasos={pasosDelViaje(v)} />
          </Tarjeta>
        )}

        {cancelacion && <p className={e.nota}>{cancelacion}</p>}
      </div>
    );
  }

  return (
    <MarcoPasajero barraMovil="oculta">
      <PantallaConMapa
        volver={{ a: '/mis-viajes', texto: 'Volver a mis viajes' }}
        mapa={viaje.data ? <Mapa etiqueta="Mapa de tu viaje" marcadores={marcadores(viaje.data)} ruta={{ desde: viaje.data.origen, hasta: viaje.data.destino }} /> : <Mapa etiqueta="Mapa" marcadores={[]} />}
      >
        {panel}
      </PantallaConMapa>
    </MarcoPasajero>
  );
}
