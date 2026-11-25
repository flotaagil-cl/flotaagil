import { useQuery } from '@tanstack/react-query';
import { Navigate, useSearchParams } from 'react-router';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { HiloSimple } from '../chat/HiloSimple';
import e from '../diseno/diseno.module.css';
import { Tarjeta } from '../diseno/Tarjeta';
import { useTitulo } from '../diseno/titulo';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { useCanalPasajero } from './canal';
import { ContactoCentral } from './ContactoCentral';
import { MarcoPasajero } from './MarcoPasajero';

/** HU-66: soporte del pasajero con la central (un hilo por cuenta), con referencia opcional a un viaje y emergencia. */
export function Soporte() {
  const { estado } = useSesion();
  const api = useApi();
  const [parametros] = useSearchParams();
  const viaje = Number(parametros.get('viaje')) || undefined;
  const soporte = useQuery({ queryKey: ['chat', 'soporte'], queryFn: () => resultado(api.POST('/api/chat/soporte/')), retry: false });
  useCanalPasajero();

  useTitulo('Soporte', estado.fase === 'autenticada' ? estado.usuario.empresa.razon_social : undefined);

  if (estado.fase !== 'autenticada') return null;
  if (estado.usuario.rol !== 'PASAJERO') return <Navigate to={inicioDeRol(estado.usuario.rol)} replace />;

  return (
    <MarcoPasajero>
      <div className={e.paginaAngosta}>
        <h1 className={e.tituloPagina}>Soporte</h1>
        <p className={e.subtituloPagina}>Escríbele a la central. Si es urgente, llama o usa WhatsApp.</p>
        <ContactoCentral />
        <Tarjeta como="section" aria-label="Conversación con la central">
          {viaje && <p className={e.nota}>{`Tu mensaje irá sobre el viaje N.º ${viaje}.`}</p>}
          {soporte.isPending ? (
            <Cargando />
          ) : soporte.isError ? (
            <Aviso tipo="error">No pudimos abrir el soporte. Recarga la página.</Aviso>
          ) : (
            <HiloSimple id={soporte.data.id} puedeEscribir etiqueta="Mensaje para la central" viaje={viaje} />
          )}
        </Tarjeta>
      </div>
    </MarcoPasajero>
  );
}
