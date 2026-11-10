import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useNavigate } from 'react-router';
import type { components } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import estilos from '../componentes/panel.module.css';
import { FallaDeCarga } from '../flota/componentes/comunes';
import { formatearFechaHora } from '../hora/hora';
import type { CuerpoSolicitud, SolicitudRespuesta } from '../portal/api';
import { Confirmacion } from '../portal/Confirmacion';
import { FormularioSolicitud } from '../portal/FormularioSolicitud';
import { mensajeDeErrorApi } from '../reservas/errores';
import { useApi, useSesion } from '../sesion/SesionProvider';

type MiCuenta = components['schemas']['MiCuenta'];
type MiReserva = components['schemas']['MiReserva'];

const CLAVE = ['mi-cuenta'] as const;

/** HU-35: la cuenta del pasajero ve sus reservas (también las de invitado), pide y cancela sin conductor. */
export function MisReservas() {
  const api = useApi();
  const cuenta = useQuery({ queryKey: CLAVE, queryFn: () => resultado(api.GET('/api/mi-cuenta/')) });
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Mis reservas</h1>
      </div>
      {cuenta.isPending ? (
        <Cargando />
      ) : cuenta.isError ? (
        <FallaDeCarga error={cuenta.error} que="tu cuenta" reintentar={() => void cuenta.refetch()} />
      ) : (
        <Cuenta cuenta={cuenta.data} />
      )}
    </section>
  );
}

function Cuenta({ cuenta }: { cuenta: MiCuenta }) {
  const [pidiendo, setPidiendo] = useState(false);
  return (
    <>
      <p>
        Hola, {cuenta.nombre}. Tus viajes con {cuenta.empresa}.
      </p>
      {pidiendo ? (
        <PedirViaje cuenta={cuenta} alTerminar={() => setPidiendo(false)} />
      ) : (
        <div className={estilos.acciones}>
          <button type="button" className={estilos.boton} onClick={() => setPidiendo(true)}>
            Pedir un viaje
          </button>
        </div>
      )}
      <Reservas />
      <EliminarCuenta />
    </>
  );
}

function PedirViaje({ cuenta, alTerminar }: { cuenta: MiCuenta; alTerminar: () => void }) {
  const api = useApi();
  const cliente = useQueryClient();
  const empresa = useQuery({
    queryKey: ['mi-cuenta', 'empresa', cuenta.empresa_slug],
    queryFn: () => resultado(api.GET('/api/portal/{slug}/', { params: { path: { slug: cuenta.empresa_slug } } })),
  });
  const [enviada, setEnviada] = useState<{ cuerpo: CuerpoSolicitud; respuesta: SolicitudRespuesta } | null>(null);
  const solicitar = useMutation({
    mutationFn: (cuerpo: CuerpoSolicitud) => resultado(api.POST('/api/mi-cuenta/solicitudes/', { body: cuerpo })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ['mi-cuenta', 'reservas'] }),
  });
  if (empresa.isPending) return <Cargando />;
  if (empresa.isError) return <FallaDeCarga error={empresa.error} que="el formulario" reintentar={() => void empresa.refetch()} />;
  if (enviada) {
    return <Confirmacion {...enviada} destacado="Tu número ya está verificado: no necesitas confirmar por WhatsApp." alHacerOtra={alTerminar} />;
  }
  return (
    <FormularioSolicitud
      empresa={empresa.data}
      solicitar={solicitar.mutateAsync}
      intro="Con tu cuenta no necesitas confirmar por WhatsApp."
      pasajeroFijo={{ nombre: cuenta.nombre, telefono: cuenta.telefono }}
      alEnviar={setEnviada}
      alNoDisponible={() => void empresa.refetch()}
    />
  );
}

function Reservas() {
  const api = useApi();
  const cliente = useQueryClient();
  const reservas = useQuery({ queryKey: ['mi-cuenta', 'reservas'], queryFn: () => resultado(api.GET('/api/mi-cuenta/reservas/')) });
  const [falla, setFalla] = useState<string | null>(null);
  const cancelar = useMutation({
    mutationFn: (id: number) => resultado(api.POST('/api/mi-cuenta/reservas/{id}/cancelar/', { params: { path: { id } } })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ['mi-cuenta', 'reservas'] }),
  });
  if (reservas.isPending) return <Cargando />;
  if (reservas.isError) return <FallaDeCarga error={reservas.error} que="tus reservas" reintentar={() => void reservas.refetch()} />;
  if (reservas.data.results.length === 0) return <p>Aún no tienes reservas.</p>;
  return (
    <>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <ul className={estilos.listaAcciones} aria-label="Mis reservas">
        {reservas.data.results.map((reserva: MiReserva) => (
          <li key={reserva.id} className={estilos.tarjeta}>
            <h2>
              {formatearFechaHora(reserva.recogida_en)} · {reserva.estado_texto}
            </h2>
            <p>
              {reserva.origen_dir} → {reserva.destino_dir}
            </p>
            <details>
              <summary>Historial</summary>
              <ol>
                {reserva.historial.map((h, i) => (
                  <li key={i}>
                    {formatearFechaHora(h.creado_en)} · {h.estado_nuevo}
                  </li>
                ))}
              </ol>
            </details>
            {reserva.cancelable && (
              <button
                type="button"
                className={estilos.botonSecundario}
                disabled={cancelar.isPending}
                onClick={() => {
                  setFalla(null);
                  cancelar.mutate(reserva.id, { onError: (error) => setFalla(mensajeDeErrorApi(error)) });
                }}
              >
                Cancelar reserva
              </button>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

function EliminarCuenta() {
  const api = useApi();
  const { sesion } = useSesion();
  const navegar = useNavigate();
  const [confirmando, setConfirmando] = useState(false);
  const [falla, setFalla] = useState<string | null>(null);
  const eliminar = useMutation({
    mutationFn: async () => {
      const { response } = await api.DELETE('/api/mi-cuenta/');
      if (!response.ok) throw new ErrorApi(response.status, null);
    },
  });
  return (
    <div className={estilos.tarjeta}>
      <h2>Eliminar mi cuenta</h2>
      <p>Se borran tu correo y tu contraseña. Tus viajes quedan registrados como de invitado.</p>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {confirmando ? (
        <div className={estilos.acciones} role="alertdialog" aria-label="Confirmar eliminación">
          <button
            type="button"
            className={estilos.botonPeligro}
            disabled={eliminar.isPending}
            onClick={() =>
              eliminar.mutate(undefined, {
                onSuccess: async () => {
                  await sesion.logout();
                  navegar('/login', { replace: true });
                },
                onError: (error) => setFalla(mensajeDeErrorApi(error)),
              })
            }
          >
            Sí, eliminar mi cuenta
          </button>
          <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando(false)}>
            Volver
          </button>
        </div>
      ) : (
        <button type="button" className={estilos.botonSecundario} onClick={() => setConfirmando(true)}>
          Eliminar mi cuenta…
        </button>
      )}
    </div>
  );
}
