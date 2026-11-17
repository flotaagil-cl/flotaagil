import { useMutation } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useParams } from 'react-router';
import { ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Boton } from '../../diseno/Boton';
import e from '../../diseno/diseno.module.css';
import { useContextoPortal } from '../contexto';

const PUNTAJES = [1, 2, 3, 4, 5] as const;

/**
 * HU-56 (CC-22): la encuesta del correo al finalizar el viaje. Registra la misma calificación de HU-24, una sola vez
 * y de forma opcional (RN-14).
 */
export function Encuesta() {
  const { api, empresa, slug } = useContextoPortal();
  const { token = '' } = useParams();
  const calificar = useMutation({
    mutationFn: (puntaje: number) =>
      resultado(api.POST('/api/portal/{slug}/encuesta/', { params: { path: { slug } }, body: { token, puntaje } })),
  });

  useEffect(() => {
    document.title = `¿Cómo fue tu viaje? · ${empresa.razon_social}`;
  }, [empresa.razon_social]);

  const estado = calificar.error instanceof ErrorApi ? calificar.error.estado : 0;
  if (calificar.isSuccess || estado === 409) {
    return (
      <section className={e.paginaAngosta}>
        <h1 className={e.tituloPagina}>¡Gracias por tu opinión!</h1>
        <p className={e.subtituloPagina}>{estado === 409 ? 'Este viaje ya tenía tu calificación.' : 'Nos ayuda a mejorar el servicio.'}</p>
      </section>
    );
  }
  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-encuesta">
      <h1 id="titulo-encuesta" className={e.tituloPagina}>
        ¿Cómo fue tu viaje?
      </h1>
      <p className={e.subtituloPagina}>Califícalo del 1 (malo) al 5 (excelente). Es opcional.</p>
      {calificar.isError && <Aviso tipo="error">{estado === 400 ? 'El enlace no es válido o ya venció.' : 'No pudimos registrar tu respuesta. Intenta de nuevo.'}</Aviso>}
      <div className={e.formulario} role="group" aria-label="Calificación">
        {PUNTAJES.map((puntaje) => (
          <Boton key={puntaje} variante="secundario" ancho disabled={calificar.isPending} onClick={() => calificar.mutate(puntaje)}>
            {puntaje} {puntaje === 1 ? 'estrella' : 'estrellas'}
          </Boton>
        ))}
      </div>
    </section>
  );
}
