import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link, useNavigate } from 'react-router';
import type { components } from '../../api/esquema';
import { ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import estilos from '../../componentes/panel.module.css';
import { Campo } from '../../formularios/Campo';
import { CampoFechaHora } from '../../formularios/CampoFechaHora';
import campos from '../../formularios/formularios.module.css';
import { aIso, instanteDeCampo, type ValorFechaHora } from '../../hora/hora';
import { useApi } from '../../sesion/SesionProvider';
import { mensajeDeErrorApi } from '../errores';

type Cuerpo = components['schemas']['ReservaContingenciaRequest'];
type Resultado = 'FINALIZADO' | 'CANCELADO';

const VACIO: ValorFechaHora = { pared: '', ocurrencia: 'primera' };
const SENTIDOS = [
  { valor: 'URBANO', texto: 'Urbano' },
  { valor: 'HACIA_AEROPUERTO', texto: 'Hacia el aeropuerto' },
  { valor: 'DESDE_AEROPUERTO', texto: 'Desde el aeropuerto' },
] as const;
const METODOS = [
  { valor: 'EFECTIVO', texto: 'Efectivo' },
  { valor: 'TARJETA', texto: 'Tarjeta' },
  { valor: 'TRANSFERENCIA', texto: 'Transferencia' },
] as const;

type Errores = Partial<Record<string, string>>;

/**
 * HU-32 (DC-33): el despachador ingresa un viaje anotado en papel durante una caída, con su folio y sus horas
 * reales. Queda finalizado o cancelado, sin avisos ni encuesta.
 */
export function Contingencia() {
  const api = useApi();
  const cliente = useQueryClient();
  const navegar = useNavigate();
  const conductores = useQuery({
    queryKey: ['reservas', 'contingencia', 'conductores'],
    queryFn: () => resultado(api.GET('/api/viajes/contingencia/conductores/')),
  });
  const crear = useMutation({
    mutationFn: (cuerpo: Cuerpo) => resultado(api.POST('/api/viajes/contingencia/', { body: cuerpo })),
    onSuccess: () => void cliente.invalidateQueries({ queryKey: ['viajes'] }),
  });
  const [datos, setDatos] = useState({
    folio: '',
    nombre: '',
    telefono: '',
    sentido: 'URBANO',
    origen_dir: '',
    destino_dir: '',
    conductor: '',
    metodo: 'EFECTIVO',
    monto: '',
    motivo: '',
  });
  const [resultadoViaje, setResultadoViaje] = useState<Resultado>('FINALIZADO');
  const [recogida, setRecogida] = useState<ValorFechaHora>(VACIO);
  const [termino, setTermino] = useState<ValorFechaHora>(VACIO);
  const [errores, setErrores] = useState<Errores>({});
  const [falla, setFalla] = useState<string | null>(null);
  const finalizado = resultadoViaje === 'FINALIZADO';
  const cambiar = (campo: keyof typeof datos) => (valor: string) => setDatos({ ...datos, [campo]: valor });

  function validar(): { errores: Errores; cuerpo?: Cuerpo } {
    const e: Errores = {};
    if (!/^[A-Za-z0-9-]{1,20}$/.test(datos.folio.trim())) e.folio = 'Hasta 20 letras, números o guiones.';
    if (!datos.nombre.trim()) e.nombre = 'Ingresa el nombre del pasajero.';
    if (!/^\+[1-9]\d{7,14}$/.test(datos.telefono.replace(/[\s-]/g, ''))) e.telefono = 'Formato E.164, p. ej. +56912345678.';
    if (!datos.origen_dir.trim()) e.origen_dir = 'Ingresa el origen.';
    if (!datos.destino_dir.trim()) e.destino_dir = 'Ingresa el destino.';
    const r = instanteDeCampo(recogida);
    const t = instanteDeCampo(termino);
    if (!r.ok) e.recogida_en = r.mensaje;
    if (!t.ok) e.termino_en = t.mensaje;
    if (finalizado) {
      if (!datos.conductor) e.conductor = 'Elige el conductor.';
      if (!/^\d{1,6}$/.test(datos.monto.trim())) e.monto = 'Monto en pesos enteros.';
    } else if (!datos.motivo.trim()) {
      e.motivo = 'Indica el motivo de la cancelación.';
    }
    if (Object.keys(e).length || !r.ok || !t.ok) return { errores: e };
    return {
      errores: e,
      cuerpo: {
        folio: datos.folio.trim(),
        pasajero: { nombre: datos.nombre.trim(), telefono: datos.telefono.replace(/[\s-]/g, '') },
        sentido: datos.sentido as Cuerpo['sentido'],
        origen_dir: datos.origen_dir.trim(),
        destino_dir: datos.destino_dir.trim(),
        resultado: resultadoViaje,
        recogida_en: aIso(r.instante),
        termino_en: aIso(t.instante),
        ...(datos.conductor && { conductor: Number(datos.conductor) }),
        ...(finalizado ? { metodo: datos.metodo as Cuerpo['metodo'], monto: Number(datos.monto) } : { motivo: datos.motivo.trim() }),
      },
    };
  }

  async function enviar(evento: FormEvent) {
    evento.preventDefault();
    setFalla(null);
    const { errores: encontrados, cuerpo } = validar();
    setErrores(encontrados);
    if (!cuerpo) return;
    try {
      const viaje = await crear.mutateAsync(cuerpo);
      navegar(`/reservas/${viaje.id}`, { replace: true, state: { aviso: `Reserva de contingencia ${viaje.folio_contingencia} ingresada.` } });
    } catch (error) {
      if (error instanceof ErrorApi && error.estado === 400) {
        const cuerpoError = (error.cuerpo ?? {}) as Record<string, string[] | undefined>;
        const delServidor: Errores = {};
        for (const [campo, mensajes] of Object.entries(cuerpoError)) if (mensajes?.[0]) delServidor[campo] = mensajes[0];
        setErrores(delServidor);
        if (!Object.keys(delServidor).length) setFalla(mensajeDeErrorApi(error));
      } else {
        setFalla(mensajeDeErrorApi(error));
      }
    }
  }

  const texto = (campo: keyof typeof datos, etiqueta: string, props: Record<string, unknown> = {}) => (
    <Campo etiqueta={etiqueta} error={errores[campo === 'nombre' ? 'nombre' : campo]}>
      {(control) => <input {...control} {...props} value={datos[campo]} onChange={(e) => cambiar(campo)(e.target.value)} />}
    </Campo>
  );

  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Reserva de contingencia</h1>
      </div>
      <p>Para los viajes anotados en papel durante una caída del sistema. Usa las horas reales de la hoja; se aceptan hasta 7 días atrás.</p>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <form className={estilos.tarjeta} onSubmit={(e) => void enviar(e)} noValidate>
        {texto('folio', 'Folio de la hoja')}
        {texto('nombre', 'Nombre del pasajero', { autoComplete: 'off' })}
        {texto('telefono', 'Teléfono (WhatsApp)', { type: 'tel' })}
        <label className={campos.campo}>
          Sentido
          <select value={datos.sentido} onChange={(e) => cambiar('sentido')(e.target.value)}>
            {SENTIDOS.map((s) => (
              <option key={s.valor} value={s.valor}>
                {s.texto}
              </option>
            ))}
          </select>
        </label>
        {texto('origen_dir', 'Origen')}
        {texto('destino_dir', 'Destino')}
        <fieldset className={campos.campo}>
          <legend>Resultado</legend>
          <label>
            <input type="radio" name="resultado" checked={finalizado} onChange={() => setResultadoViaje('FINALIZADO')} /> Finalizado
          </label>
          <label>
            <input type="radio" name="resultado" checked={!finalizado} onChange={() => setResultadoViaje('CANCELADO')} /> Cancelado
          </label>
        </fieldset>
        <CampoFechaHora etiqueta="Recogida real" nombre="recogida_en" valor={recogida} alCambiar={setRecogida} error={errores.recogida_en} />
        <CampoFechaHora
          etiqueta={finalizado ? 'Término real' : 'Hora de la cancelación'}
          nombre="termino_en"
          valor={termino}
          alCambiar={setTermino}
          error={errores.termino_en}
        />
        <Campo etiqueta="Conductor" error={errores.conductor}>
          {(control) => (
            <select {...control} value={datos.conductor} onChange={(e) => cambiar('conductor')(e.target.value)}>
              <option value="">{finalizado ? 'Elige el conductor' : 'Sin conductor'}</option>
              {(conductores.data ?? []).map((c) => (
                <option key={c.id} value={c.id}>
                  {c.nombre}
                </option>
              ))}
            </select>
          )}
        </Campo>
        {finalizado ? (
          <>
            <label className={campos.campo}>
              Método de pago
              <select value={datos.metodo} onChange={(e) => cambiar('metodo')(e.target.value)}>
                {METODOS.map((m) => (
                  <option key={m.valor} value={m.valor}>
                    {m.texto}
                  </option>
                ))}
              </select>
            </label>
            {texto('monto', 'Monto cobrado (CLP)', { inputMode: 'numeric' })}
          </>
        ) : (
          <Campo etiqueta="Motivo de la cancelación" error={errores.motivo}>
            {(control) => <textarea {...control} rows={3} maxLength={200} value={datos.motivo} onChange={(e) => cambiar('motivo')(e.target.value)} />}
          </Campo>
        )}
        <div className={estilos.acciones}>
          <button type="submit" className={estilos.boton} disabled={crear.isPending}>
            {crear.isPending ? 'Guardando…' : 'Ingresar reserva'}
          </button>
          <Link to="/reservas" className={estilos.botonSecundario}>
            Volver
          </Link>
        </div>
      </form>
    </section>
  );
}
