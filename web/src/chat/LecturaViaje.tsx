/**
 * HU-66 (CP-55): la central lee el chat entre el conductor y el pasajero de una reserva, en solo lectura. Cada vez que
 * se abre queda en la auditoría, por eso se carga solo al pedirlo.
 */

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import estilos from '../componentes/panel.module.css';
import { Boton } from '../diseno/Boton';
import { Dialogo } from '../diseno/Dialogo';
import { formatearFechaHora } from '../hora/hora';
import { useApi } from '../sesion/SesionProvider';
import c from './chat.module.css';

export function LecturaViaje({ viaje }: { viaje: number }) {
  const api = useApi();
  const [abierto, setAbierto] = useState(false);
  const lectura = useQuery({
    queryKey: ['chat', 'lectura', viaje],
    queryFn: () => resultado(api.GET('/api/chat/viajes/{viaje_id}/lectura/', { params: { path: { viaje_id: viaje } } })),
    enabled: abierto,
    gcTime: 0,
    staleTime: 0,
  });

  return (
    <div className={estilos.tarjeta}>
      <h2>Chat del viaje</h2>
      <p className={estilos.explicacion}>Mensajes entre el conductor y el pasajero. Solo lectura; cada lectura queda registrada en la auditoría.</p>
      <Boton variante="secundario" onClick={() => setAbierto(true)}>
        Ver chat con el pasajero
      </Boton>
      <Dialogo abierto={abierto} titulo="Chat del viaje (solo lectura)" onCerrar={() => setAbierto(false)}>
        <Aviso>Esta lectura quedó registrada en la auditoría.</Aviso>
        {lectura.isPending ? (
          <Cargando />
        ) : lectura.isError ? (
          <Aviso tipo="error">No se pudo cargar el chat. Intenta de nuevo.</Aviso>
        ) : lectura.data.results.length === 0 ? (
          <p className={c.vacio}>El conductor y el pasajero aún no se han escrito.</p>
        ) : (
          <ol className={c.mensajes} aria-label="Mensajes del viaje">
            {lectura.data.results.map((m) => (
              <li key={m.id} className={c.ajeno}>
                <span className={c.autor}>{m.autor}</span>
                <p className={c.cuerpo}>{m.texto}</p>
                <span className={c.detalle}>{formatearFechaHora(m.creado_en)}</span>
              </li>
            ))}
          </ol>
        )}
      </Dialogo>
    </div>
  );
}
