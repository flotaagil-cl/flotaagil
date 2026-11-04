import { useEffect, useMemo, useState } from 'react';
import { Aviso } from '../componentes/Aviso';
import estilos from '../componentes/panel.module.css';
import { useEntorno } from '../entornoContexto';
import { useSesion } from '../sesion/SesionProvider';
import { ConexionMapa, urlDelMapa, type CrearSocket, type EstadoMapa } from './conexion';
import { antiguedad, confianza, type ConductorMapa } from './estado';
import { MapaEsquematico } from './MapaEsquematico';
import { MapaGoogle } from './MapaGoogle';
import propios from './mapa.module.css';

const ESTADOS = { DISPONIBLE: 'Disponible', EN_VIAJE: 'En viaje' } as const;
const MOTIVOS = {
  sin_posicion: 'Sin posición todavía',
  antigua: 'Posición de hace más de 60 s: no confiable',
  imprecisa: 'Posición imprecisa (más de 100 m): no confiable',
} as const;
const TICK_MS = 5000;

function hace(segundos: number | null): string {
  if (segundos === null) return 'sin posición';
  if (segundos < 60) return `hace ${segundos} s`;
  return `hace ${Math.floor(segundos / 60)} min`;
}

/**
 * Mapa en tiempo real de los conductores en turno (HU-02). Con clave usa Google Maps; sin ella, o si no carga, el
 * esquemático. La clave va en `web/.env`, que está ignorado. `crearSocket` se reemplaza en las pruebas.
 */
export function Mapa({ crearSocket }: { crearSocket?: CrearSocket }) {
  const claveMapa = import.meta.env.VITE_GOOGLE_MAPS_KEY as string | undefined;
  const entorno = useEntorno();
  const { sesion } = useSesion();
  const conexion = useMemo(() => new ConexionMapa(urlDelMapa(entorno.origen), sesion, crearSocket, () => entorno.ahora()), [entorno, sesion, crearSocket]);
  const [estado, setEstado] = useState<EstadoMapa>(conexion.estado);
  const [seleccionado, setSeleccionado] = useState<number | null>(null);
  const [ahora, setAhora] = useState(() => entorno.ahora());
  const [fallaGoogle, setFallaGoogle] = useState(false);

  useEffect(() => {
    const quitar = conexion.suscribir(setEstado);
    conexion.iniciar();
    return () => {
      quitar();
      conexion.detener();
    };
  }, [conexion]);

  // Las antigüedades y la marca de «no confiable» avanzan aunque no lleguen mensajes.
  useEffect(() => {
    const reloj = setInterval(() => setAhora(entorno.ahora()), TICK_MS);
    return () => clearInterval(reloj);
  }, [entorno]);

  const conductores = [...estado.conductores.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es'));
  const elegido = seleccionado === null ? null : estado.conductores.get(seleccionado) ?? null;
  const momento = Math.max(ahora, ...[...estado.recibidas.values()]);

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Mapa</h1>
        <p className={propios.estadoConexion} aria-live="polite">
          {estado.fase === 'conectado'
            ? `En vivo · ${conductores.length} ${conductores.length === 1 ? 'conductor' : 'conductores'} en turno`
            : estado.fase === 'reconectando'
              ? 'Reconectando…'
              : estado.fase === 'sin_sesion'
                ? 'La sesión terminó.'
                : 'Conectando…'}
        </p>
      </div>
      {estado.fase === 'reconectando' && <Aviso tipo="error">Se perdió la conexión en vivo. Reintentando…</Aviso>}

      {claveMapa && fallaGoogle && <Aviso tipo="error">No se pudo cargar Google Maps: se muestra el mapa esquemático.</Aviso>}

      <div className={propios.disposicion}>
        {claveMapa && !fallaGoogle ? (
          <MapaGoogle
            clave={claveMapa}
            conductores={conductores}
            seleccionado={seleccionado}
            alSeleccionar={setSeleccionado}
            ahora={momento}
            alFallar={() => setFallaGoogle(true)}
          />
        ) : (
          <MapaEsquematico conductores={conductores} seleccionado={seleccionado} alSeleccionar={setSeleccionado} ahora={momento} />
        )}
        <div>
          {elegido && <Ficha conductor={elegido} ahora={momento} />}
          {conductores.length === 0 && estado.fase === 'conectado' ? (
            <p>No hay conductores en turno.</p>
          ) : (
            <ul className={propios.lista} aria-label="Conductores en turno">
              {conductores.map((conductor) => {
                const confia = confianza(conductor, momento);
                return (
                  <li key={conductor.id}>
                    <button type="button" aria-pressed={conductor.id === seleccionado} onClick={() => setSeleccionado(conductor.id)}>
                      <strong>{conductor.nombre}</strong>
                      <span>
                        {conductor.patente ?? 'Sin vehículo'} · {ESTADOS[conductor.estado]} · {hace(antiguedad(conductor, momento))}
                      </span>
                      {!confia.confiable && <span className={propios.noConfiable}>{MOTIVOS[confia.motivo]}</span>}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}

function Ficha({ conductor, ahora }: { conductor: ConductorMapa; ahora: number }) {
  const confia = confianza(conductor, ahora);
  return (
    <div className={estilos.tarjeta} aria-label="Conductor seleccionado" role="region">
      <h2>{conductor.nombre}</h2>
      <dl className={estilos.datos}>
        <div>
          <dt>Patente</dt>
          <dd>{conductor.patente ?? 'Sin vehículo declarado'}</dd>
        </div>
        <div>
          <dt>Estado</dt>
          <dd>{ESTADOS[conductor.estado]}</dd>
        </div>
        <div>
          <dt>Última posición</dt>
          <dd>
            {hace(antiguedad(conductor, ahora))}
            {conductor.posicion?.precision_m != null && ` · ±${conductor.posicion.precision_m} m`}
            {!confia.confiable && <span className={estilos.alerta}>{MOTIVOS[confia.motivo]}</span>}
          </dd>
        </div>
      </dl>
    </div>
  );
}
