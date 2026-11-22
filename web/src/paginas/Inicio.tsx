import { useState } from 'react';
import { Link } from 'react-router';
import { Icono } from '../diseno/Icono';
import type { NombreIcono } from '../diseno/iconos';
import { hoy } from '../hora/hora';
import { useSesion } from '../sesion/SesionProvider';
import { TEXTO_FASE, type FaseIndicadores } from './conexionIndicadores';
import { Indicadores } from './Indicadores';
import estilos from './Inicio.module.css';

interface Atajo {
  a: string;
  titulo: string;
  texto: string;
  icono: NombreIcono;
  alerta?: 'peligro' | 'aviso';
}

/** Indicadores del día (HU-01) y atajos al listado filtrado. */
export function Inicio() {
  const { estado } = useSesion();
  const [fase, setFase] = useState<FaseIndicadores>('conectando');
  if (estado.fase !== 'autenticada') return null;

  const atajos: Atajo[] = [
    { a: `/reservas?fecha=${hoy()}`, titulo: 'Reservas de hoy', texto: 'Recogidas del día (hora de Santiago).', icono: 'calendario' },
    { a: '/reservas?estado=PENDIENTE_CONFIRMACION', titulo: 'Por confirmar', texto: 'Esperan la confirmación del pasajero por correo.', icono: 'reloj' },
    {
      a: '/reservas?sin_confirmar=true&desde=',
      titulo: 'Sin confirmar',
      texto: 'Venció el plazo: confírmalas por teléfono o cancélalas.',
      icono: 'alerta',
      alerta: 'peligro',
    },
    {
      a: '/reservas?estado=SOLICITADO',
      titulo: 'Sin asignar',
      texto: 'Solicitadas, todavía sin conductor.',
      icono: 'alerta',
      alerta: 'aviso',
    },
    { a: '/reservas', titulo: 'Próximas', texto: 'Todas desde hoy 00:00.', icono: 'lista' },
  ];

  const moduloActivo = estado.usuario.empresa.modulo_cuentas;

  return (
    <section className={estilos.pagina}>
      <header className={estilos.cabeceraInicio}>
        <div className={estilos.tituloBloque}>
          <h1>Inicio</h1>
          {/* DC-51 (CC-22): el módulo lo activa FlotaÁgil; aquí solo se informa. */}
          <p className={estilos.subtitulo}>
            <span>Resumen operativo</span>
            <span className={estilos.separador} aria-hidden="true">
              ·
            </span>
            <span>Hola, {estado.usuario.nombre}.</span>
            <span className={estilos.separador} aria-hidden="true">
              ·
            </span>
            <span className={moduloActivo ? estilos.badgeModuloActivo : estilos.badgeModuloInactivo}>
              {moduloActivo ? 'Módulo de convenios activo' : 'Formularios públicos'}
            </span>
          </p>
        </div>

        <div className={estilos.accionesCabecera}>
          <span className={estilos.estadoVivo} data-fase={fase} aria-live="polite">
            <span className={estilos.puntoVivo} aria-hidden="true" />
            {TEXTO_FASE[fase]}
          </span>
          <Link to="/reservas/nueva" className={estilos.boton}>
            <Icono nombre="mas" tamano={18} />
            Nueva reserva
          </Link>
        </div>
      </header>

      <Indicadores alCambiarFase={setFase} />

      <div className={estilos.bloqueAtajos}>
        <h2 className={estilos.tituloSeccion}>Accesos rápidos de gestión</h2>
        <ul className={estilos.atajos} aria-label="Atajos a las reservas">
          {atajos.map((atajo) => (
            <li key={atajo.a}>
              <Link to={atajo.a} className={estilos.tarjetaAtajo} data-alerta={atajo.alerta}>
                <div className={estilos.cabeceraAtajo}>
                  <span className={estilos.iconoAtajo}>
                    <Icono nombre={atajo.icono} tamano={18} />
                  </span>
                  <Icono nombre="flechaDerecha" tamano={16} className={estilos.flechaAtajo} />
                </div>
                <strong>{atajo.titulo}</strong>
                <span>{atajo.texto}</span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
