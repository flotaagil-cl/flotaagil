import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../componentes/Aviso';
import estilos from '../componentes/panel.module.css';
import { Icono } from '../diseno/Icono';
import { proveedorDelEntorno } from '../diseno/mapa/proveedor';
import { useEntorno } from '../entornoContexto';
import { tieneModulo } from '../rutas/tabla';
import { useSesion } from '../sesion/SesionProvider';
import { ConexionMapa, urlDelMapa, type CrearSocket, type EstadoMapa } from './conexion';
import { antiguedad, confianza, type ConductorMapa } from './estado';
import propios from './mapa.module.css';
import { MapaEsquematico } from './MapaEsquematico';
import { MapaGoogle } from './MapaGoogle';
import { MapaOsm } from './MapaOsm';

const ESTADOS = { DISPONIBLE: 'Disponible', EN_VIAJE: 'En viaje' } as const;
const MOTIVOS = {
  sin_posicion: 'Sin posición todavía',
  antigua: 'Posición de hace más de 60 s: no confiable',
  imprecisa: 'Posición imprecisa (más de 100 m): no confiable',
} as const;
const TICK_MS = 5000;

type FiltroLista = 'TODOS' | 'DISPONIBLES' | 'EN_VIAJE' | 'CON_GPS';

const FILTROS: { clave: FiltroLista; etiqueta: string }[] = [
  { clave: 'TODOS', etiqueta: 'Todos' },
  { clave: 'DISPONIBLES', etiqueta: 'Disponibles' },
  { clave: 'EN_VIAJE', etiqueta: 'En viaje' },
  { clave: 'CON_GPS', etiqueta: 'Con GPS' },
];

function hace(segundos: number | null): string {
  if (segundos === null) return 'sin posición';
  if (segundos < 60) return `hace ${segundos} s`;
  const minutos = Math.floor(segundos / 60);
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) {
    const restoMin = minutos % 60;
    return restoMin > 0 ? `hace ${horas} h ${restoMin} min` : `hace ${horas} h`;
  }
  const dias = Math.floor(horas / 24);
  const restoHoras = horas % 24;
  return restoHoras > 0 ? `hace ${dias} d ${restoHoras} h` : `hace ${dias} d`;
}

function normalizarTexto(valor: string): string {
  return valor
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();
}

function infoSenal(conductor: ConductorMapa, ahora: number): { tipo: 'activa' | 'antigua' | 'sin_senal'; texto: string; clase: string } {
  const confia = confianza(conductor, ahora);
  const segundos = antiguedad(conductor, ahora);
  if (confia.confiable) {
    return { tipo: 'activa', texto: `GPS activo · ${hace(segundos)}`, clase: propios.senalActiva };
  }
  if (confia.motivo === 'sin_posicion') {
    return { tipo: 'sin_senal', texto: 'Sin señal GPS', clase: propios.senalSin };
  }
  if (confia.motivo === 'imprecisa') {
    return { tipo: 'antigua', texto: `GPS impreciso (±${conductor.posicion?.precision_m ?? 0} m)`, clase: propios.senalAlerta };
  }
  return { tipo: 'antigua', texto: `Señal antigua · ${hace(segundos)}`, clase: propios.senalAlerta };
}

/**
 * Mapa en tiempo real de los conductores en turno (HU-02). El proveedor sale de `VITE_MAPA_PROVEEDOR` (HU-70): Google
 * con clave, OpenStreetMap en desarrollo o el esquemático; si el elegido no carga, el esquemático. La clave va en
 * `web/.env`, que está ignorado. `crearSocket` se reemplaza en las pruebas.
 */
export function Mapa({ crearSocket }: { crearSocket?: CrearSocket }) {
  const claveMapa = import.meta.env.VITE_GOOGLE_MAPS_KEY as string | undefined;
  const proveedor = proveedorDelEntorno();
  const entorno = useEntorno();
  const { sesion, estado: estadoSesion } = useSesion();
  const conexion = useMemo(() => new ConexionMapa(urlDelMapa(entorno.origen), sesion, crearSocket, () => entorno.ahora()), [entorno, sesion, crearSocket]);
  const [estado, setEstado] = useState<EstadoMapa>(conexion.estado);
  const [seleccionado, setSeleccionado] = useState<number | null>(null);
  const [ahora, setAhora] = useState(() => entorno.ahora());
  const [fallaMapa, setFallaMapa] = useState(false);
  const [busqueda, setBusqueda] = useState('');
  const [filtro, setFiltro] = useState<FiltroLista>('TODOS');
  const [reencuadrar, setReencuadrar] = useState(0);
  const [enfoque, setEnfoque] = useState(0);

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

  const conductores = useMemo(
    () => [...estado.conductores.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, 'es')),
    [estado.conductores],
  );
  const elegido = seleccionado === null ? null : estado.conductores.get(seleccionado) ?? null;
  const momento = Math.max(ahora, ...[...estado.recibidas.values()]);

  const conteos = useMemo(() => {
    let disponibles = 0;
    let enViaje = 0;
    let conGps = 0;
    let activos = 0;
    for (const c of conductores) {
      if (c.estado === 'DISPONIBLE') disponibles += 1;
      else enViaje += 1;
      if (c.posicion) {
        conGps += 1;
        if (confianza(c, momento).confiable) activos += 1;
      }
    }
    return { TODOS: conductores.length, DISPONIBLES: disponibles, EN_VIAJE: enViaje, CON_GPS: conGps, activos };
  }, [conductores, momento]);

  const conductoresFiltrados = useMemo(() => {
    const termino = normalizarTexto(busqueda.trim());
    return conductores.filter((conductor) => {
      if (filtro === 'DISPONIBLES' && conductor.estado !== 'DISPONIBLE') return false;
      if (filtro === 'EN_VIAJE' && conductor.estado !== 'EN_VIAJE') return false;
      if (filtro === 'CON_GPS' && !conductor.posicion) return false;
      if (!termino) return true;
      const coincideNombre = normalizarTexto(conductor.nombre).includes(termino);
      const coincidePatente = conductor.patente ? normalizarTexto(conductor.patente).includes(termino) : false;
      return coincideNombre || coincidePatente;
    });
  }, [conductores, busqueda, filtro]);

  const conductoresEnMapa = useMemo(() => {
    if (!elegido || conductoresFiltrados.some((c) => c.id === elegido.id)) return conductoresFiltrados;
    return [...conductoresFiltrados, elegido];
  }, [conductoresFiltrados, elegido]);

  const modulos = estadoSesion.fase === 'autenticada' ? estadoSesion.usuario.modulos : undefined;
  const puedeVerConductores = tieneModulo(modulos, 'CONDUCTORES');
  const puedeVerReservas = tieneModulo(modulos, 'RESERVAS');

  function seleccionarConductor(conductor: ConductorMapa) {
    setSeleccionado(conductor.id);
    if (conductor.posicion) {
      setEnfoque((n) => n + 1);
    }
  }

  return (
    <section className={propios.paginaMapa}>
      <div className={propios.cabeceraOperativa}>
        <div className={propios.tituloBloque}>
          <h1>Mapa de flota en vivo</h1>
          <p className={propios.subtitulo}>
            Seguimiento GPS en tiempo real
            {conductores.length > 0 && ` · ${conteos.CON_GPS} en mapa (${conteos.activos} ${conteos.activos === 1 ? 'activo' : 'activos'})`}
          </p>
        </div>
        <div className={propios.accionesCabecera}>
          <p className={propios.badgeVivo} data-fase={estado.fase} aria-live="polite">
            {estado.fase === 'conectado' && <span className={propios.puntoVivo} aria-hidden="true" />}
            {estado.fase === 'conectado'
              ? `En vivo · ${conductores.length} ${conductores.length === 1 ? 'conductor' : 'conductores'} en turno`
              : estado.fase === 'reconectando'
                ? 'Reconectando…'
                : estado.fase === 'sin_sesion'
                  ? 'La sesión terminó.'
                  : 'Conectando…'}
          </p>
          <button
            type="button"
            className={propios.botonCentrar}
            disabled={conteos.CON_GPS === 0}
            onClick={() => setReencuadrar((n) => n + 1)}
          >
            <Icono nombre="destino" tamano={16} />
            Centrar flota
          </button>
        </div>
      </div>

      {estado.fase === 'reconectando' && <Aviso tipo="error">Se perdió la conexión en vivo. Reintentando…</Aviso>}

      {fallaMapa && (
        <Aviso tipo="error">
          No se pudo cargar {proveedor === 'google' ? 'Google Maps' : 'OpenStreetMap'}: se muestra el mapa esquemático.
        </Aviso>
      )}

      <div className={propios.disposicion}>
        <div className={propios.marcoMapa}>
          {proveedor === 'google' && claveMapa && !fallaMapa ? (
            <MapaGoogle
              clave={claveMapa}
              conductores={conductoresEnMapa}
              seleccionado={seleccionado}
              alSeleccionar={setSeleccionado}
              ahora={momento}
              alFallar={() => setFallaMapa(true)}
              reencuadrar={reencuadrar}
              enfoque={enfoque}
            />
          ) : proveedor === 'osm' && !fallaMapa ? (
            <MapaOsm
              conductores={conductoresEnMapa}
              seleccionado={seleccionado}
              alSeleccionar={setSeleccionado}
              ahora={momento}
              alFallar={() => setFallaMapa(true)}
              reencuadrar={reencuadrar}
              enfoque={enfoque}
            />
          ) : (
            <MapaEsquematico conductores={conductoresEnMapa} seleccionado={seleccionado} alSeleccionar={setSeleccionado} ahora={momento} />
          )}

          <div className={propios.leyendaMapa} aria-label="Leyenda del mapa">
            <span className={propios.leyendaItem}>
              <span className={`${propios.leyendaPunto} ${propios.leyendaDisponible}`} aria-hidden="true" />
              Disponible
            </span>
            <span className={propios.leyendaItem}>
              <span className={`${propios.leyendaPunto} ${propios.leyendaEnViaje}`} aria-hidden="true" />
              En viaje
            </span>
            <span className={propios.leyendaItem}>
              <span className={`${propios.leyendaPunto} ${propios.leyendaNoConfiable}`} aria-hidden="true" />
              Señal no confiable
            </span>
          </div>
        </div>

        <aside className={propios.panelLateral} aria-label="Panel de conductores en turno">
          <div className={propios.panelCabecera}>
            <div className={propios.panelTituloFila}>
              <h2>Conductores en turno</h2>
              <span className={propios.contadorPanel}>
                {conductoresFiltrados.length}/{conductores.length}
              </span>
            </div>
            <input
              type="search"
              className={propios.buscador}
              aria-label="Buscar conductor o patente"
              placeholder="Buscar conductor o patente..."
              value={busqueda}
              onChange={(evento) => setBusqueda(evento.target.value)}
            />
            <div className={propios.chipsFiltro} role="group" aria-label="Filtrar conductores">
              {FILTROS.map((item) => (
                <button
                  key={item.clave}
                  type="button"
                  className={propios.chipFiltro}
                  aria-label={item.etiqueta}
                  aria-pressed={filtro === item.clave}
                  onClick={() => setFiltro(item.clave)}
                >
                  <span>{item.etiqueta}</span>
                  <span className={propios.conteoChip} aria-hidden="true">
                    {conteos[item.clave]}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {elegido && (
            <div className={propios.fichaFija}>
              <Ficha
                conductor={elegido}
                ahora={momento}
                alCerrar={() => setSeleccionado(null)}
                alCentrar={() => setEnfoque((n) => n + 1)}
                puedeVerConductores={puedeVerConductores}
                puedeVerReservas={puedeVerReservas}
              />
            </div>
          )}

          <div className={propios.cuerpoPanel}>
            {conductores.length === 0 && estado.fase === 'conectado' ? (
              <p className={propios.vacioLista}>No hay conductores en turno.</p>
            ) : conductoresFiltrados.length === 0 && conductores.length > 0 ? (
              <p className={propios.vacioLista}>Ningún conductor coincide con el filtro.</p>
            ) : (
              <ul className={propios.lista} aria-label="Conductores en turno">
                {conductoresFiltrados.map((conductor) => {
                  const senal = infoSenal(conductor, momento);
                  const esDisponible = conductor.estado === 'DISPONIBLE';
                  return (
                    <li key={conductor.id}>
                      <button
                        type="button"
                        className={propios.tarjetaConductor}
                        data-senal={senal.tipo}
                        aria-pressed={conductor.id === seleccionado}
                        onClick={() => seleccionarConductor(conductor)}
                      >
                        <div className={propios.tarjetaCabecera}>
                          <strong className={propios.nombreConductor}>{conductor.nombre}</strong>
                          <span className={`${propios.badgeEstado} ${esDisponible ? propios.estadoDisponible : propios.estadoEnViaje}`}>
                            {ESTADOS[conductor.estado]}
                          </span>
                        </div>
                        <div className={propios.tarjetaMeta}>
                          <span className={propios.patente}>{conductor.patente ?? 'Sin patente'}</span>
                          <span className={`${propios.senalGps} ${senal.clase}`}>
                            <span className={propios.puntoSenal} aria-hidden="true" />
                            {senal.texto}
                          </span>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </aside>
      </div>
    </section>
  );
}

function Ficha({
  conductor,
  ahora,
  alCerrar,
  alCentrar,
  puedeVerConductores,
  puedeVerReservas,
}: {
  conductor: ConductorMapa;
  ahora: number;
  alCerrar: () => void;
  alCentrar: () => void;
  puedeVerConductores: boolean;
  puedeVerReservas: boolean;
}) {
  const confia = confianza(conductor, ahora);
  return (
    <div className={propios.fichaCompacta} aria-label="Conductor seleccionado" role="region">
      <div className={propios.fichaCabecera}>
        <h2>{conductor.nombre}</h2>
        <button type="button" className={propios.cerrarFicha} aria-label="Cerrar ficha" onClick={alCerrar}>
          <Icono nombre="cerrar" tamano={15} />
        </button>
      </div>
      <dl className={propios.fichaDatos}>
        <div>
          <dt>Patente</dt>
          <dd>{conductor.patente ?? 'Sin vehículo declarado'}</dd>
        </div>
        <div>
          <dt>Estado</dt>
          <dd>{ESTADOS[conductor.estado]}</dd>
        </div>
        <div className={propios.fichaPosicion}>
          <dt>Última posición</dt>
          <dd>
            {hace(antiguedad(conductor, ahora))}
            {conductor.posicion?.precision_m != null && ` · ±${conductor.posicion.precision_m} m`}
            {!confia.confiable && <span className={estilos.alerta}>{MOTIVOS[confia.motivo]}</span>}
          </dd>
        </div>
      </dl>
      <div className={propios.fichaAcciones}>
        <button type="button" className={propios.botonFicha} disabled={!conductor.posicion} onClick={alCentrar}>
          <Icono nombre="destino" tamano={14} aria-hidden="true" />
          Centrar en mapa
        </button>
        {puedeVerConductores && (
          <Link to={`/conductores/${conductor.id}`} className={propios.enlaceFicha}>
            Ver ficha
          </Link>
        )}
        {conductor.estado === 'EN_VIAJE' && puedeVerReservas && (
          <Link to="/reservas?estado=EN_CAMINO" className={propios.enlaceFicha}>
            Viajes en curso
          </Link>
        )}
      </div>
    </div>
  );
}
