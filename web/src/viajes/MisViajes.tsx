import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { Link, Navigate } from 'react-router';
import { resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import { claseBoton } from '../diseno/clases';
import e from '../diseno/diseno.module.css';
import { Icono } from '../diseno/Icono';
import { Segmentado } from '../diseno/Segmentado';
import { Insignia } from '../diseno/Tarjeta';
import { formatearFechaHora } from '../hora/hora';
import { inicioDeRol } from '../rutas/tabla';
import { useApi, useSesion } from '../sesion/SesionProvider';
import { MarcoPasajero } from './MarcoPasajero';
import { INSIGNIA, esAnterior, tramo } from './viaje';

/**
 * HU-44: «Mis viajes» del pasajero, próximos y anteriores; cada uno abre «Tu viaje», donde se cancela si aún no
 * tiene conductor (RN-09).
 */
export function MisViajes() {
  const { estado } = useSesion();
  const api = useApi();
  const [vista, setVista] = useState<'proximos' | 'anteriores'>('proximos');
  const viajes = useQuery({ queryKey: ['mi-cuenta', 'viajes'], queryFn: () => resultado(api.GET('/api/mi-cuenta/reservas/')) });

  useEffect(() => {
    document.title = 'Mis viajes';
  }, []);

  if (estado.fase !== 'autenticada') return null;
  if (estado.usuario.rol !== 'PASAJERO') return <Navigate to={inicioDeRol(estado.usuario.rol)} replace />;

  const todos = viajes.data?.results ?? [];
  const proximos = todos.filter((v) => !esAnterior(v.estado)).sort((a, b) => a.recogida_en.localeCompare(b.recogida_en));
  const anteriores = todos.filter((v) => esAnterior(v.estado));
  const lista = vista === 'proximos' ? proximos : anteriores;

  return (
    <MarcoPasajero>
      <div className={e.paginaAngosta}>
        <div className={e.tituloConInsignia}>
          <h1 className={e.tituloPagina}>Mis viajes</h1>
          <Link to="/pedir" className={claseBoton('principal')}>
            Pedir traslado
          </Link>
        </div>
        <Segmentado
          etiqueta="Mostrar"
          forma="pastillas"
          valor={vista}
          onCambiar={setVista}
          opciones={[
            { valor: 'proximos', texto: `Próximos (${proximos.length})` },
            { valor: 'anteriores', texto: 'Anteriores' },
          ]}
        />
        {viajes.isPending && <Cargando />}
        {viajes.isError && <Aviso tipo="error">No pudimos cargar tus viajes. Recarga la página.</Aviso>}
        {viajes.isSuccess && lista.length === 0 && (
          <p className={e.saludo}>{vista === 'proximos' ? 'No tienes viajes próximos.' : 'Todavía no tienes viajes anteriores.'}</p>
        )}
        <ul className={e.listaViajes}>
          {lista.map((v) => {
            const insignia = INSIGNIA[v.estado ?? 'SOLICITADO'];
            return (
              <li key={v.id}>
                <Link to={`/mis-viajes/${v.id}`} className={e.opcionViaje}>
                  <span className={e.opcionIcono}>
                    <Icono nombre={v.sentido === 'DESDE_AEROPUERTO' ? 'aterrizaje' : v.sentido === 'HACIA_AEROPUERTO' ? 'despegue' : 'auto'} />
                  </span>
                  <span className={e.viajeTexto}>
                    <span className={e.opcionTitulo}>{tramo(v)}</span>
                    <span className={e.opcionDetalle}>
                      {formatearFechaHora(v.recogida_en)} · N.º {v.id}
                    </span>
                  </span>
                  <Insignia tono={insignia.tono}>{insignia.texto}</Insignia>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </MarcoPasajero>
  );
}
