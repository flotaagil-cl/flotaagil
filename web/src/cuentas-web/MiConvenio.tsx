import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import type { components } from '../api/esquema';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import estilos from '../componentes/panel.module.css';
import { Celda, FallaDeCarga } from '../flota/componentes/comunes';
import { formatearFechaHora } from '../hora/hora';
import type { CuerpoSolicitud, SolicitudRespuesta } from '../portal/api';
import { Confirmacion } from '../portal/Confirmacion';
import { FormularioSolicitud } from '../portal/FormularioSolicitud';
import { useApi } from '../sesion/SesionProvider';

type MiConvenioDatos = components['schemas']['MiConvenio'];

function useMiConvenio() {
  const api = useApi();
  return useQuery({ queryKey: ['mi-convenio'], queryFn: () => resultado(api.GET('/api/mi-convenio/')) });
}

function useEmpresaPublica(slug: string | undefined) {
  const api = useApi();
  return useQuery({
    queryKey: ['mi-convenio', 'empresa', slug],
    enabled: Boolean(slug),
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug: slug! } } })),
  });
}

function useReservas() {
  const api = useApi();
  return useQuery({ queryKey: ['mi-convenio', 'reservas'], queryFn: () => resultado(api.GET('/api/mi-convenio/reservas/')) });
}

/** HU-34: cuenta de la empresa con convenio. En revisión o rechazada ve su estado; aprobada pide viajes. */
export function MiConvenio() {
  const convenio = useMiConvenio();
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Mi convenio</h1>
      </div>
      {convenio.isPending ? (
        <Cargando />
      ) : convenio.isError ? (
        <FallaDeCarga error={convenio.error} que="tu convenio" reintentar={() => void convenio.refetch()} />
      ) : (
        <Cuenta convenio={convenio.data} />
      )}
    </section>
  );
}

function Cuenta({ convenio }: { convenio: MiConvenioDatos }) {
  return (
    <>
      <p>
        {convenio.cliente_nombre} · convenio con {convenio.empresa}
      </p>
      {convenio.estado === 'EN_REVISION' && (
        <Aviso>Tu registro está en revisión. Te avisaremos por correo cuando {convenio.empresa} lo apruebe; mientras tanto no puedes pedir viajes.</Aviso>
      )}
      {convenio.estado === 'RECHAZADO' && (
        <Aviso tipo="error">
          {convenio.empresa} no aprobó el convenio. Motivo: {convenio.motivo_rechazo}
        </Aviso>
      )}
      {convenio.estado === 'APROBADO' && <PedirViaje slug={convenio.empresa_slug} />}
      <Reservas />
    </>
  );
}

function PedirViaje({ slug }: { slug: string }) {
  const api = useApi();
  const cliente = useQueryClient();
  const empresa = useEmpresaPublica(slug);
  const [enviada, setEnviada] = useState<{ cuerpo: CuerpoSolicitud; respuesta: SolicitudRespuesta } | null>(null);
  const [vuelta, setVuelta] = useState(0);
  const solicitar = useMutation({
    mutationFn: (cuerpo: CuerpoSolicitud) =>
      resultado(
        api.POST('/api/mi-convenio/solicitudes/', { body: { ...cuerpo, declara_autorizacion: cuerpo.declara_autorizacion ?? false } }),
      ),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ['mi-convenio', 'reservas'] }),
  });
  if (empresa.isPending) return <Cargando />;
  if (empresa.isError) return <FallaDeCarga error={empresa.error} que="el formulario" reintentar={() => void empresa.refetch()} />;
  if (enviada) {
    return (
      <Confirmacion
        {...enviada}
        destacado="La reserva quedó registrada sin verificación por WhatsApp (RN-07)."
        alHacerOtra={() => {
          setEnviada(null);
          setVuelta((n) => n + 1);
        }}
      />
    );
  }
  return (
    <FormularioSolicitud
      key={vuelta}
      empresa={empresa.data}
      solicitar={solicitar.mutateAsync}
      intro="Pide un viaje a nombre de tu empresa. Queda solicitado de inmediato."
      leyendaDatos="Datos del pasajero"
      conDeclaracion
      alEnviar={setEnviada}
      alNoDisponible={() => void empresa.refetch()}
    />
  );
}

function Reservas() {
  const reservas = useReservas();
  if (reservas.isPending) return <Cargando />;
  if (reservas.isError) return <FallaDeCarga error={reservas.error} que="las reservas" reintentar={() => void reservas.refetch()} />;
  if (reservas.data.results.length === 0) return <p>Aún no hay reservas con tu convenio.</p>;
  return (
    <table className={estilos.tabla} aria-label="Reservas del convenio">
      <thead>
        <tr>
          <th scope="col">Recogida</th>
          <th scope="col">Pasajero</th>
          <th scope="col">Trayecto</th>
          <th scope="col">Estado</th>
        </tr>
      </thead>
      <tbody>
        {reservas.data.results.map((r) => (
          <tr key={r.id}>
            <Celda titulo="Recogida">{formatearFechaHora(r.recogida_en)}</Celda>
            <Celda titulo="Pasajero">{r.pasajero}</Celda>
            <Celda titulo="Trayecto">
              {r.origen_dir} → {r.destino_dir}
            </Celda>
            <Celda titulo="Estado">{r.estado_texto}</Celda>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
