import { useState } from 'react';
import { Link } from 'react-router';
import { Cargando } from '../../componentes/Cargando';
import estilos from '../../componentes/panel.module.css';
import { Boton } from '../../diseno/Boton';
import { claseBoton } from '../../diseno/clases';
import { FallaDeCarga } from '../../flota/componentes/comunes';
import { formatearFechaHora } from '../../hora/hora';
import { useModeracion } from '../api';
import c from '../chat.module.css';
import { GestionGrupo } from './GestionGrupo';

/** HU-62: el administrador modera los grupos con sus metadatos (nombre, integrantes y fechas), sin leer los mensajes. */
export function Moderacion() {
  const consulta = useModeracion();
  const [gestionar, setGestionar] = useState<number | null>(null);
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Moderación del chat</h1>
        <Link to="/chat" className={`${claseBoton('secundario')} ${c.botonCompacto}`}>
          Volver al chat
        </Link>
      </div>
      <p className={estilos.explicacion}>
        Por privacidad (Código del Trabajo, art. 5) no ves los mensajes de los grupos ni de los directos en los que no participas. Puedes renombrar un grupo,
        quitar integrantes o borrarlo; cada acción queda en la auditoría.
      </p>
      {consulta.isPending ? (
        <Cargando />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="los grupos" reintentar={() => void consulta.refetch()} />
      ) : consulta.data.length === 0 ? (
        <p className={estilos.vacio}>No hay grupos.</p>
      ) : (
        <>
          <p className={c.moderacionResumen}>
            {`${consulta.data.length} ${consulta.data.length === 1 ? 'grupo registrado' : 'grupos registrados'}`}
          </p>
          <div className={c.tablaTarjeta}>
            <div className={c.tablaEnvoltura}>
              <table className={estilos.tabla}>
                <thead>
                  <tr>
                    <th scope="col">Grupo</th>
                    <th scope="col">Integrantes</th>
                    <th scope="col">Creado</th>
                    <th scope="col">Último mensaje</th>
                    <th scope="col">
                      <span className="solo-lector">Acciones</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {consulta.data.map((grupo) => (
                    <tr key={grupo.id}>
                      <td data-titulo="Grupo" className={c.celdaNombre}>
                        {grupo.nombre}
                      </td>
                      <td data-titulo="Integrantes">
                        {`${grupo.integrantes.length} · ${grupo.integrantes.map((i) => i.nombre).join(', ')}`}
                      </td>
                      <td data-titulo="Creado">
                        {formatearFechaHora(grupo.creado_en)}
                        {grupo.creado_por && ` · ${grupo.creado_por}`}
                      </td>
                      <td data-titulo="Último mensaje" className={grupo.ultimo_mensaje_en ? undefined : c.celdaTenue}>
                        {grupo.ultimo_mensaje_en ? formatearFechaHora(grupo.ultimo_mensaje_en) : 'Sin mensajes'}
                      </td>
                      <td data-titulo="Acciones">
                        <Boton
                          variante="secundario"
                          className={c.botonFila}
                          aria-label={`Gestionar ${grupo.nombre}`}
                          onClick={() => setGestionar(grupo.id)}
                        >
                          Gestionar
                        </Boton>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
      {gestionar !== null && <GestionGrupo id={gestionar} abierto cerrar={() => setGestionar(null)} puedeAgregar={false} puedeBorrar />}
    </section>
  );
}
