import { useState } from 'react';
import { useSolicitar, type Solicitud, type SolicitudRespuesta } from '../api';
import { Confirmacion } from '../Confirmacion';
import { useContextoPortal } from '../contexto';
import { FormularioSolicitud } from '../FormularioSolicitud';
import { NoDisponible } from '../NoDisponible';

interface Enviada {
  cuerpo: Solicitud;
  respuesta: SolicitudRespuesta;
}

/**
 * Formulario del portal. Tras enviar muestra la confirmación en la misma ruta, sin guardar nada en el
 * navegador: con F5 se vuelve al formulario vacío.
 */
export function Solicitar() {
  const { api, empresa, slug } = useContextoPortal();
  const solicitar = useSolicitar(api, slug);
  const [enviada, setEnviada] = useState<Enviada | null>(null);
  const [vuelta, setVuelta] = useState(0);
  const [noDisponible, setNoDisponible] = useState(false);
  if (noDisponible) return <NoDisponible />;
  if (enviada) {
    return (
      <Confirmacion
        {...enviada}
        alHacerOtra={() => {
          setEnviada(null);
          setVuelta((n) => n + 1); // formulario nuevo, vacío
        }}
      />
    );
  }
  return (
    <FormularioSolicitud
      key={vuelta}
      empresa={empresa}
      solicitar={solicitar.mutateAsync}
      intro={`Te enviaremos un WhatsApp para confirmar tu solicitud. Tendrás ${empresa.expiracion_verificacion_min} minutos para responderlo.`}
      alEnviar={setEnviada}
      alNoDisponible={() => setNoDisponible(true)}
    />
  );
}
