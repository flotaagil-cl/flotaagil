import { useMutation } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import type { components } from '../../api/esquema';
import { ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Boton } from '../../diseno/Boton';
import { Campo, Casilla } from '../../diseno/Campo';
import e from '../../diseno/diseno.module.css';
import { Pestanas } from '../../diseno/Pestanas';
import { formatearFechaHora } from '../../hora/hora';
import { FormularioPedido } from '../../pedido/FormularioPedido';
import { resumenPedido, TIPOS, type CuerpoPedido, type TipoPedido, type ValoresPedido } from '../../pedido/pedido';
import { useContextoPortal } from '../contexto';

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

function validar(c: Contacto): Errores {
  const errores: Errores = {};
  if (!c.nombre.trim()) errores.nombre = 'Escribe tu nombre.';
  if (!/^\S+@\S+\.\S+$/.test(c.correo.trim())) errores.correo = 'Escribe un correo válido: ahí te llega el enlace para confirmar.';
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
 */
export function ReservaPublica() {
  const { api, empresa, slug } = useContextoPortal();
  const [tipo, setTipo] = useState<TipoPedido>('en-la-ciudad');
  const [etapa, setEtapa] = useState<Etapa>({ fase: 'formulario' });
  const [contacto, setContacto] = useState<Contacto>(CONTACTO);
  const [errores, setErrores] = useState<Errores>({});

  useEffect(() => {
    document.title = `Pedir un traslado · ${empresa.razon_social}`;
  }, [empresa.razon_social]);

  const enviar = useMutation({
    mutationFn: (cuerpo: CuerpoPedido) =>
      resultado(
        api.POST('/api/portal/{slug}/reservas/', {
          params: { path: { slug } },
          body: { ...cuerpo, ...contacto, nombre: contacto.nombre.trim(), correo: contacto.correo.trim() },
        }),
      ),
    onSuccess: (respuesta) => setEtapa({ fase: 'enviada', respuesta, correo: contacto.correo.trim() }),
    onError: (error) => {
      if (error instanceof ErrorApi && error.estado === 400) setErrores(erroresDe(error.cuerpo));
      else if (error instanceof ErrorApi && error.estado === 429) setErrores({ general: 'Enviaste varias solicitudes seguidas. Espera un rato e intenta de nuevo.' });
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
    return (
      <section className={e.paginaAngosta} aria-labelledby="titulo-enviada">
        <h1 id="titulo-enviada" className={e.tituloPagina}>
          Revisa tu correo
        </h1>
        <p className={e.subtituloPagina}>
          Te enviamos a <strong>{etapa.correo}</strong> el enlace para confirmar tu reserva. Ábrelo antes del{' '}
          {formatearFechaHora(etapa.respuesta.confirmar_hasta)}.
        </p>
        <Aviso>Hasta que la confirmes, la reserva queda pendiente. Si no te llega, revisa la carpeta de spam.</Aviso>
      </section>
    );
  }

  if (etapa.fase === 'contacto') {
    const { cuerpo, valores } = etapa;
    const actual = TIPOS.find((t) => t.id === etapa.tipo)!;
    const alEnviar = (evento: FormEvent) => {
      evento.preventDefault();
      const encontrados = validar(contacto);
      setErrores(encontrados);
      if (Object.keys(encontrados).length === 0) enviar.mutate(cuerpo);
    };
    return (
      <section className={e.paginaAngosta} aria-labelledby="titulo-contacto">
        <h1 id="titulo-contacto" className={e.tituloPagina}>
          Tus datos
        </h1>
        <section className={e.resumen} aria-label="Tu viaje">
          <h2 className={e.resumenTitulo}>{actual.titulo}</h2>
          <dl className={e.resumenFilas}>
            {resumenPedido(etapa.tipo, valores, cuerpo, empresa).map(([etiqueta, valor]) => (
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
        <form className={e.formulario} onSubmit={alEnviar} noValidate aria-label="Tus datos">
          {errores.general && <Aviso tipo="error">{errores.general}</Aviso>}
          <Campo etiqueta="Nombre y apellido" autoComplete="name" value={contacto.nombre} error={errores.nombre} onChange={(ev) => cambiar('nombre', ev.target.value)} />
          <Campo
            etiqueta="Correo"
            type="email"
            autoComplete="email"
            value={contacto.correo}
            error={errores.correo}
            ayuda="Te enviaremos el enlace para confirmar y los avisos de tu viaje."
            onChange={(ev) => cambiar('correo', ev.target.value)}
          />
          <Campo etiqueta="Teléfono de contacto" type="tel" autoComplete="tel" value={contacto.telefono} error={errores.telefono} onChange={(ev) => cambiar('telefono', ev.target.value)} />
          <Casilla checked={contacto.es_empresa} onChange={(ev) => cambiar('es_empresa', ev.target.checked)}>
            ¿Es una empresa?
          </Casilla>
          {contacto.es_empresa && (
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
      <p className={e.subtituloPagina}>Pide tu traslado sin crear una cuenta. Te confirmamos por correo.</p>
      <Pestanas etiqueta="Tipo de viaje" pestanas={TIPOS} activa={tipo} onCambiar={(id) => setTipo(id as TipoPedido)}>
        <FormularioPedido
          key={`${tipo}-${etapa.valores ? 'borrador' : 'nuevo'}`}
          tipo={tipo}
          empresa={empresa}
          iniciales={etapa.valores}
          alRevisar={(valores, cuerpo) => {
            setErrores({});
            setEtapa({ fase: 'contacto', tipo, valores, cuerpo });
          }}
        />
      </Pestanas>
    </section>
  );
}
