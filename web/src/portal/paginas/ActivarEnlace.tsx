import { useMutation } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { Link, useParams } from 'react-router';
import { codigoDe, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import { claseBoton } from '../../diseno/clases';
import e from '../../diseno/diseno.module.css';
import { useTitulo } from '../../diseno/titulo';
import { useContextoPortal } from '../contexto';

const MENSAJES: Record<string, { titulo: string; texto: string }> = {
  enlace_vencido: { titulo: 'El enlace venció', texto: 'Vale 24 horas. Pide uno nuevo desde «Activa tu cuenta».' },
  enlace_invalido: { titulo: 'El enlace no es válido', texto: 'Revisa que lo copiaste completo desde el correo.' },
  telefono_en_uso: {
    titulo: 'No pudimos activar tu cuenta',
    texto: 'Ese teléfono ya tiene una cuenta en esta empresa. Si es tuyo, contacta a la empresa.',
  },
};

/**
 * HU-64 (DC-61, CP-56): el enlace del correo activa la cuenta. Se activa con un POST al abrir la página (no al
 * cargar el correo: los revisores de enlaces no deben activarla solos) y una sola vez aunque el efecto corra dos.
 */
export function ActivarEnlace() {
  const { api, empresa, slug } = useContextoPortal();
  const { token = '' } = useParams();
  const activar = useMutation({
    mutationFn: () => resultado(api.POST('/api/portal/{slug}/cuenta/activar/', { params: { path: { slug } }, body: { token } })),
  });
  const { mutate } = activar;
  const enviado = useRef(false);

  useTitulo('Activar cuenta', empresa.razon_social);

  useEffect(() => {
    if (enviado.current) return;
    enviado.current = true;
    mutate();
  }, [mutate]);

  if (activar.isPending || activar.isIdle) return <Cargando />;
  if (activar.isError) {
    const codigo = codigoDe(activar.error) ?? '';
    const mensaje = MENSAJES[codigo] ?? { titulo: 'No pudimos activar tu cuenta', texto: 'Intenta de nuevo en un momento.' };
    return (
      <section className={e.paginaAngosta}>
        <h1 className={e.tituloPagina}>{mensaje.titulo}</h1>
        <Aviso tipo={codigo === 'enlace_vencido' ? 'info' : 'error'}>{mensaje.texto}</Aviso>
        {codigo === 'enlace_vencido' && (
          <Link to={`/solicitar/${slug}/activar`} className={claseBoton('principal', true)}>
            Pedir un enlace nuevo
          </Link>
        )}
      </section>
    );
  }
  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-activada">
      <h1 id="titulo-activada" className={e.tituloPagina}>
        ¡Tu cuenta está activa!
      </h1>
      <p className={e.subtituloPagina}>Ya puedes ingresar con tu correo y contraseña para pedir tus traslados.</p>
      <Link to={`/solicitar/${slug}/ingresar`} className={claseBoton('principal', true)}>
        Ingresar
      </Link>
    </section>
  );
}
