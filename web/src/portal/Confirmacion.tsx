import { useEffect, useRef, type ReactNode } from 'react';
import { formatearFechaHora } from '../hora/hora';
import type { Solicitud } from './api';
import { SENTIDOS } from './formulario';
import { mostrarTelefono } from './telefono';
import estilos from './portal.module.css';

interface Props {
  cuerpo: Solicitud;
  /** `expira_en` solo existe si hay que confirmar por WhatsApp; con convenio no (RN-07). */
  respuesta: { recogida_en: string; mensaje: string; expira_en?: string };
  /** Reemplaza la instrucción de confirmar por WhatsApp. */
  destacado?: ReactNode;
  alHacerOtra: () => void;
}

/**
 * Solicitud recibida: lo pedido, el plazo para confirmar por WhatsApp (expira_en, en hora de Chile) y la
 * instrucción. Sin número de reserva: la API no lo devuelve. No se guarda en el navegador.
 */
export function Confirmacion({ cuerpo, respuesta, destacado, alHacerOtra }: Props) {
  const titulo = useRef<HTMLHeadingElement>(null);
  useEffect(() => titulo.current?.focus(), []);
  const sentido = SENTIDOS.find((s) => s.valor === cuerpo.sentido)?.texto;
  return (
    <section className={estilos.tarjeta} aria-labelledby="titulo-confirmacion">
      <h1 id="titulo-confirmacion" ref={titulo} tabIndex={-1}>
        Solicitud recibida
      </h1>
      <p className={estilos.destacado}>
        {destacado ?? (
          <>
            Confirma respondiendo el WhatsApp que enviamos al <strong>{mostrarTelefono(cuerpo.telefono)}</strong> antes del{' '}
            <strong>{formatearFechaHora(respuesta.expira_en!)}</strong> (hora de Chile).
          </>
        )}
      </p>
      <p>{respuesta.mensaje}</p>
      <h2>Lo que pediste</h2>
      <dl className={estilos.resumen}>
        <dt>Nombre</dt>
        <dd>{cuerpo.nombre}</dd>
        <dt>WhatsApp</dt>
        <dd>{mostrarTelefono(cuerpo.telefono)}</dd>
        {sentido && (
          <>
            <dt>Viaje</dt>
            <dd>{sentido}</dd>
          </>
        )}
        {cuerpo.vuelo && (
          <>
            <dt>Vuelo</dt>
            <dd>
              {cuerpo.vuelo.numero} · llegada {formatearFechaHora(cuerpo.vuelo.hora_llegada)}
            </dd>
          </>
        )}
        <dt>Origen</dt>
        <dd>{cuerpo.origen_dir}</dd>
        <dt>Destino</dt>
        <dd>{cuerpo.destino_dir}</dd>
        <dt>Recogida</dt>
        <dd>
          {formatearFechaHora(respuesta.recogida_en)} (hora de Chile)
          {!cuerpo.recogida_en && <span className={estilos.nota}> · calculada con la llegada de tu vuelo</span>}
        </dd>
      </dl>
      <button type="button" className={estilos.botonSecundario} onClick={alHacerOtra}>
        Hacer otra solicitud
      </button>
    </section>
  );
}
