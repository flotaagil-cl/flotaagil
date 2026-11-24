import { useMutation } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import type { components } from '../../api/esquema';
import { detalleDe, ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Boton } from '../../diseno/Boton';
import { Campo, Casilla, DatoFijo } from '../../diseno/Campo';
import e from '../../diseno/diseno.module.css';
import { Pestanas } from '../../diseno/Pestanas';
import { Segmentado } from '../../diseno/Segmentado';
import { formatearFechaHora } from '../../hora/hora';
import { FormularioPedido } from '../../pedido/FormularioPedido';
import { resumenPedido, TIPOS, type CuerpoPedido, type TipoPedido, type ValoresPedido } from '../../pedido/pedido';
import { AccesoConvenio, TarjetaPase } from '../AccesoConvenio';
import { useContextoPortal } from '../contexto';
import {
  borrarPase,
  cuerpoConvenio,
  DATOS_CONVENIO,
  erroresConvenioDelServidor,
  leerPase,
  validarConvenio,
  type DatosConvenio,
  type ErroresConvenio,
  type PaseConvenio,
} from '../convenio';
import { PersonasConvenio } from '../PersonasConvenio';

type Respuesta = components['schemas']['ReservaPublicaRespuesta'];

interface Contacto {
  nombre: string;
  telefono: string;
  correo: string;
  es_empresa: boolean;
  empresa_razon_social: string;
  empresa_rut: string;
  empresa_contacto: string;
  acepta_privacidad: boolean;
  sitio_web: string;
}

const CONTACTO: Contacto = {
  nombre: '',
  telefono: '',
  correo: '',
  es_empresa: false,
  empresa_razon_social: '',
  empresa_rut: '',
  empresa_contacto: '',
  acepta_privacidad: false,
  sitio_web: '',
};

type Errores = Partial<Record<keyof Contacto | 'general', string>>;

type Etapa =
  | { fase: 'formulario'; valores?: ValoresPedido }
  | { fase: 'contacto'; tipo: TipoPedido; valores: ValoresPedido; cuerpo: CuerpoPedido }
  | { fase: 'enviada'; respuesta: Respuesta; correo: string };

type Modo = 'natural' | 'empresa';

/** Primer mensaje de cada campo que devuelve el backend (400). */
function erroresDe(cuerpo: unknown): Errores {
  const salida: Errores = {};
  if (cuerpo && typeof cuerpo === 'object') {
    for (const [campo, mensajes] of Object.entries(cuerpo as Record<string, unknown>)) {
      const texto = Array.isArray(mensajes) ? String(mensajes[0]) : typeof mensajes === 'string' ? mensajes : null;
      if (texto) salida[(campo in CONTACTO ? campo : 'general') as keyof Errores] = texto;
    }
  }
  return salida;
}

function validar(c: Contacto, conPase = false): Errores {
  const errores: Errores = {};
  if (!c.nombre.trim()) errores.nombre = 'Escribe tu nombre.';
  if (!conPase && !/^\S+@\S+\.\S+$/.test(c.correo.trim())) errores.correo = 'Escribe un correo válido: ahí te llega el enlace para confirmar.';
  if (!c.telefono.trim()) errores.telefono = 'Escribe un teléfono de contacto.';
  if (c.es_empresa) {
    if (!c.empresa_razon_social.trim()) errores.empresa_razon_social = 'Escribe la razón social.';
    if (!c.empresa_rut.trim()) errores.empresa_rut = 'Escribe el RUT de la empresa.';
    if (!c.empresa_contacto.trim()) errores.empresa_contacto = 'Escribe la persona de contacto.';
  }
  if (!c.acepta_privacidad) errores.acepta_privacidad = 'Debes aceptar el aviso de privacidad.';
  return errores;
}

/**
 * HU-51 (CC-22): reserva pública sin cuenta, para las empresas sin el módulo de cuentas. Primero el viaje (el mismo
 * formulario de /pedir), después los datos de contacto y el aviso de privacidad. La reserva queda pendiente hasta
 * que el pasajero abre el enlace que le llega por correo.
 *
 * CC-23 (HU-73): sin el módulo de cuentas, «¿Quién pide?» elige entre pasajero natural (lo de siempre) y empresa con
 * convenio: primero correo + clave (pase), después el viaje y quién viaja. La reserva queda a nombre de quien pide.
 */
export function ReservaPublica() {
  const { api, empresa, slug } = useContextoPortal();
  const [tipo, setTipo] = useState<TipoPedido>('en-la-ciudad');
  const [etapa, setEtapa] = useState<Etapa>({ fase: 'formulario' });
  const [contacto, setContacto] = useState<Contacto>(CONTACTO);
  const [errores, setErrores] = useState<Errores>({});
  // CC-23 (D2): el modo empresa con clave existe solo sin el módulo de cuentas.
  const conClave = !empresa.modulo_cuentas;
  const [pase, setPase] = useState<PaseConvenio | null>(() => (conClave ? leerPase(slug) : null));
  const [modo, setModo] = useState<Modo>(pase ? 'empresa' : 'natural');
  const [avisoPase, setAvisoPase] = useState<string>();
  const [convenio, setConvenio] = useState<DatosConvenio>(DATOS_CONVENIO);
  const [erroresConvenio, setErroresConvenio] = useState<ErroresConvenio>({});
  const empresaConPase = modo === 'empresa' && pase !== null;
  const tope = empresa.convenio_max_personas;

  useEffect(() => {
    document.title = `Pedir un traslado · ${empresa.razon_social}`;
  }, [empresa.razon_social]);

  const salirDelPase = (aviso?: string) => {
    borrarPase(slug);
    setPase(null);
    setAvisoPase(aviso);
  };

  const enviar = useMutation({
    mutationFn: (cuerpo: CuerpoPedido) =>
      resultado(
        api.POST('/api/portal/{slug}/reservas/', {
          params: { path: { slug } },
          body: empresaConPase
            ? { ...cuerpo, nombre: contacto.nombre.trim(), telefono: contacto.telefono.trim(), acepta_privacidad: contacto.acepta_privacidad, sitio_web: contacto.sitio_web, ...cuerpoConvenio(convenio, pase.pase) }
            : {
                ...cuerpo,
                ...contacto,
                es_empresa: conClave ? false : contacto.es_empresa,
                nombre: contacto.nombre.trim(),
                correo: contacto.correo.trim(),
                para: 'MI',
                vehiculos: 'MISMO',
                declara_informados: false,
              },
        }),
      ),
    onSuccess: (respuesta) => setEtapa({ fase: 'enviada', respuesta, correo: empresaConPase ? pase.correo : contacto.correo.trim() }),
    onError: (error) => {
      if (error instanceof ErrorApi && error.estado === 401) {
        // CC-23: el pase venció o ya no vale (clave nueva, revocada o convenio desactivado): vuelve a la clave.
        salirDelPase(detalleDe(error) ?? 'Tu acceso de convenio venció. Ingresa de nuevo tu correo y la clave.');
        setEtapa((actual) => ({ fase: 'formulario', valores: actual.fase === 'contacto' ? actual.valores : undefined }));
        return;
      }
      if (error instanceof ErrorApi && error.estado === 400) {
        setErrores(erroresDe(error.cuerpo));
        if (empresaConPase) setErroresConvenio(erroresConvenioDelServidor(error.cuerpo));
        return;
      }
      if (error instanceof ErrorApi && error.estado === 429) setErrores({ general: 'Enviaste varias solicitudes seguidas. Espera un rato e intenta de nuevo.' });
      else setErrores({ general: 'No pudimos enviar tu solicitud. Intenta de nuevo.' });
    },
  });

  const cambiar = <K extends keyof Contacto>(campo: K, valor: Contacto[K]) => setContacto((c) => ({ ...c, [campo]: valor }));

  if (etapa.fase === 'enviada' && etapa.respuesta.confirma_convenio) {
    // HU-54: el correo no está autorizado en el convenio de su empresa; decide el contacto del convenio.
    return (
      <section className={e.paginaAngosta} aria-labelledby="titulo-enviada">
        <h1 id="titulo-enviada" className={e.tituloPagina}>
          Tu reserva espera la autorización de tu empresa
        </h1>
        <p className={e.subtituloPagina}>
          Tu correo no está autorizado en el convenio: le pedimos al contacto de tu empresa que la autorice. Te avisaremos a <strong>{etapa.correo}</strong>.
        </p>
      </section>
    );
  }

  if (etapa.fase === 'enviada') {
    const viajes = etapa.respuesta.viajes ?? 1;
    return (
      <section className={e.paginaAngosta} aria-labelledby="titulo-enviada">
        <h1 id="titulo-enviada" className={e.tituloPagina}>
          Revisa tu correo
        </h1>
        {viajes > 1 ? (
          <p className={e.subtituloPagina}>
            Creamos <strong>{viajes} traslados</strong>, uno por persona. Enviamos un solo enlace a <strong>{etapa.correo}</strong>: ábrelo antes del{' '}
            {formatearFechaHora(etapa.respuesta.confirmar_hasta)} para confirmarlos todos.
          </p>
        ) : (
          <p className={e.subtituloPagina}>
            Te enviamos a <strong>{etapa.correo}</strong> el enlace para confirmar tu reserva. Ábrelo antes del{' '}
            {formatearFechaHora(etapa.respuesta.confirmar_hasta)}.
          </p>
        )}
        <Aviso>Hasta que la confirmes, la reserva queda pendiente. Si no te llega, revisa la carpeta de spam.</Aviso>
      </section>
    );
  }

  if (etapa.fase === 'contacto') {
    const { cuerpo, valores } = etapa;
    const actual = TIPOS.find((t) => t.id === etapa.tipo)!;
    const alEnviar = (evento: FormEvent) => {
      evento.preventDefault();
      const encontrados = validar(contacto, empresaConPase);
      const deConvenio = empresaConPase ? validarConvenio(convenio, empresa.capacidad_maxima, tope) : {};
      setErrores(encontrados);
      setErroresConvenio(deConvenio);
      if (Object.keys(encontrados).length === 0 && Object.keys(deConvenio).length === 0) enviar.mutate(cuerpo);
    };
    // Con pase, los pasajeros salen de quién viaja: la fila del resumen no aplica.
    const filas = resumenPedido(etapa.tipo, valores, cuerpo, empresa).filter(([etiqueta]) => !(empresaConPase && etiqueta === 'Pasajeros'));
    return (
      <section className={e.paginaAngosta} aria-labelledby="titulo-contacto">
        <h1 id="titulo-contacto" className={e.tituloPagina}>
          {empresaConPase ? 'Quién viaja' : 'Tus datos'}
        </h1>
        {empresaConPase && <TarjetaPase pase={pase} alSalir={() => salirDelPase()} />}
        <section className={e.resumen} aria-label="Tu viaje">
          <h2 className={e.resumenTitulo}>{actual.titulo}</h2>
          <dl className={e.resumenFilas}>
            {filas.map(([etiqueta, valor]) => (
              <div key={etiqueta}>
                <dt>{etiqueta}</dt>
                <dd>{valor}</dd>
              </div>
            ))}
          </dl>
          <button type="button" className={e.botonEnlace} onClick={() => setEtapa({ fase: 'formulario', valores })}>
            Editar el viaje
          </button>
        </section>
        <form className={e.formulario} onSubmit={alEnviar} noValidate aria-label={empresaConPase ? 'Quién viaja' : 'Tus datos'}>
          {errores.general && <Aviso tipo="error">{errores.general}</Aviso>}
          {empresaConPase && <Aviso>La reserva queda a nombre de quien la pide (tú): tú la confirmas y recibes los avisos.</Aviso>}
          {empresaConPase && <h2 className={e.resumenTitulo}>Quien pide</h2>}
          <Campo etiqueta="Nombre y apellido" autoComplete="name" value={contacto.nombre} error={errores.nombre} onChange={(ev) => cambiar('nombre', ev.target.value)} />
          {empresaConPase ? (
            <DatoFijo etiqueta="Correo (el del convenio, aquí llega el enlace para confirmar)" valor={pase.correo} icono="mensaje" />
          ) : (
            <Campo
              etiqueta="Correo"
              type="email"
              autoComplete="email"
              value={contacto.correo}
              error={errores.correo}
              ayuda="Te enviaremos el enlace para confirmar y los avisos de tu viaje."
              onChange={(ev) => cambiar('correo', ev.target.value)}
            />
          )}
          <Campo etiqueta="Teléfono de contacto" type="tel" autoComplete="tel" value={contacto.telefono} error={errores.telefono} onChange={(ev) => cambiar('telefono', ev.target.value)} />
          {empresaConPase && (
            <PersonasConvenio
              slug={slug}
              datos={convenio}
              errores={erroresConvenio}
              capacidad={empresa.capacidad_maxima}
              tope={tope}
              onCambiar={setConvenio}
            />
          )}
          {/* CC-23 (DC-77): sin módulo, la empresa pide con su clave; la casilla de RUT queda solo con el módulo (HU-60). */}
          {!conClave && (
            <Casilla checked={contacto.es_empresa} onChange={(ev) => cambiar('es_empresa', ev.target.checked)}>
              ¿Es una empresa?
            </Casilla>
          )}
          {!conClave && contacto.es_empresa && (
            <>
              <Campo etiqueta="Razón social" value={contacto.empresa_razon_social} error={errores.empresa_razon_social} onChange={(ev) => cambiar('empresa_razon_social', ev.target.value)} />
              <Campo etiqueta="RUT de la empresa" placeholder="12345678-9" value={contacto.empresa_rut} error={errores.empresa_rut} onChange={(ev) => cambiar('empresa_rut', ev.target.value)} />
              <Campo etiqueta="Persona de contacto" value={contacto.empresa_contacto} error={errores.empresa_contacto} onChange={(ev) => cambiar('empresa_contacto', ev.target.value)} />
            </>
          )}
          {/* Campo trampa: oculto para las personas; un bot lo llena. */}
          <div aria-hidden="true" style={{ position: 'absolute', left: '-10000px' }}>
            <label>
              Sitio web
              <input tabIndex={-1} autoComplete="off" value={contacto.sitio_web} onChange={(ev) => cambiar('sitio_web', ev.target.value)} />
            </label>
          </div>
          <Casilla checked={contacto.acepta_privacidad} error={errores.acepta_privacidad} onChange={(ev) => cambiar('acepta_privacidad', ev.target.checked)}>
            Acepto el{' '}
            <Link to={`/solicitar/${slug}/privacidad`} target="_blank">
              aviso de privacidad
            </Link>{' '}
            (Ley 21.719).
          </Casilla>
          <Boton type="submit" ancho cargando={enviar.isPending}>
            {enviar.isPending ? 'Enviando…' : 'Enviar solicitud'}
          </Boton>
        </form>
      </section>
    );
  }

  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-pedir">
      <h1 id="titulo-pedir" className={e.tituloPagina}>
        ¿A dónde te llevamos?
      </h1>
      <p className={e.subtituloPagina}>
        {modo === 'empresa'
          ? 'Pide traslados con el convenio de tu empresa. Te confirmamos por correo.'
          : 'Pide tu traslado sin crear una cuenta. Te confirmamos por correo.'}
      </p>
      {conClave && (
        <Segmentado<Modo>
          etiqueta="¿Quién pide?"
          forma="pastillas"
          opciones={[
            { valor: 'natural', texto: 'Pasajero natural' },
            { valor: 'empresa', texto: 'Empresa con convenio' },
          ]}
          valor={modo}
          onCambiar={setModo}
        />
      )}
      {modo === 'empresa' && !pase ? (
        <AccesoConvenio
          aviso={avisoPase}
          alEntrar={(nuevo) => {
            setAvisoPase(undefined);
            setPase(nuevo);
          }}
          alPedirComoNatural={() => setModo('natural')}
        />
      ) : (
        <>
          {empresaConPase && <TarjetaPase pase={pase} alSalir={() => salirDelPase()} />}
          <Pestanas etiqueta="Tipo de viaje" pestanas={TIPOS} activa={tipo} onCambiar={(id) => setTipo(id as TipoPedido)}>
        <FormularioPedido
          key={`${tipo}-${etapa.valores ? 'borrador' : 'nuevo'}`}
          tipo={tipo}
          empresa={empresa}
          sinPasajeros={empresaConPase}
          textoBoton={empresaConPase ? 'Siguiente: quién viaja' : undefined}
          iniciales={etapa.valores}
          alRevisar={(valores, cuerpo) => {
            setErrores({});
            setEtapa({ fase: 'contacto', tipo, valores, cuerpo });
          }}
        />
          </Pestanas>
        </>
      )}
    </section>
  );
}
