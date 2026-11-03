/**
 * Estado del conductor en vivo en las pantallas de Conductores (PR-07): usan el mismo canal que el mapa
 * (/ws/mapa/, HU-02) en vez de volver a pedir los datos cada cierto tiempo.
 *
 * El canal avisa cada posición, pero solo se recargan los datos cuando cambia algo que estas pantallas muestran:
 * quién está en turno, su estado o su vehículo. Si la conexión se corta, al volver llega la foto completa y se
 * compara con la anterior, así que no se pierde un cambio ocurrido mientras tanto.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { useEntorno } from '../entornoContexto';
import { ConexionMapa, urlDelMapa, type FaseConexion } from '../mapa/conexion';
import type { ConductorMapa } from '../mapa/estado';
import { useSesion } from '../sesion/SesionProvider';
import { claves } from './api';

/** ¿Cambió quién está en turno, su estado o su vehículo? Las posiciones no cuentan. */
export function cambioEstado(
  antes: ReadonlyMap<number, ConductorMapa>,
  ahora: ReadonlyMap<number, ConductorMapa>,
): boolean {
  if (antes.size !== ahora.size) return true;
  for (const [id, conductor] of ahora) {
    const previo = antes.get(id);
    if (!previo || previo.estado !== conductor.estado || previo.patente !== conductor.patente) return true;
  }
  return false;
}

/** Mantiene al día los datos de Conductores mientras la pantalla está abierta. Devuelve el estado de la conexión. */
export function useEstadoEnVivo(): FaseConexion {
  const entorno = useEntorno();
  const { sesion } = useSesion();
  const cliente = useQueryClient();
  const conexion = useMemo(() => new ConexionMapa(urlDelMapa(entorno.origen), sesion), [entorno, sesion]);
  const [fase, setFase] = useState<FaseConexion>(conexion.estado.fase);

  useEffect(() => {
    let anteriores = conexion.estado.conductores;
    const quitar = conexion.suscribir((estado) => {
      setFase(estado.fase);
      if (cambioEstado(anteriores, estado.conductores)) {
        void cliente.invalidateQueries({ queryKey: claves.conductores });
      }
      anteriores = estado.conductores;
    });
    conexion.iniciar();
    return () => {
      quitar();
      conexion.detener();
    };
  }, [conexion, cliente]);

  return fase;
}
