import { useMutation } from '@tanstack/react-query';
import { useEffect, useState, type FormEvent } from 'react';
import { ErrorApi, resultado } from '../../api/resultado';
import { Aviso } from '../../componentes/Aviso';
import { Boton } from '../../diseno/Boton';
import { Campo } from '../../diseno/Campo';
import e from '../../diseno/diseno.module.css';
import { useContextoPortal } from '../contexto';

interface Datos {
  cliente_nombre: string;
  cliente_rut: string;
  direccion: string;
  contacto_nombre: string;
  contacto_correo: string;
  contacto_telefono: string;
  viajes_estimados_mes: string;
  correos: string;
  sitio_web: string;
}

const VACIO: Datos = {
  cliente_nombre: '',
  cliente_rut: '',
  direccion: '',
  contacto_nombre: '',
  contacto_correo: '',
  contacto_telefono: '',
  viajes_estimados_mes: '',
  correos: '',
  sitio_web: '',
};

type Errores = Partial<Record<keyof Datos | 'correos_autorizados' | 'general', string>>;

const ETIQUETAS: Record<Exclude<keyof Datos, 'correos' | 'sitio_web'>, string> = {
  cliente_nombre: 'Razón social',
  cliente_rut: 'RUT de la empresa',
  direccion: 'Dirección',
  contacto_nombre: 'Persona de contacto',
  contacto_correo: 'Correo de contacto',
  contacto_telefono: 'Teléfono de contacto',
  viajes_estimados_mes: 'Viajes estimados al mes',
};

function primerError(cuerpo: unknown): Errores {
  const salida: Errores = {};
  if (cuerpo && typeof cuerpo === 'object') {
    for (const [campo, valor] of Object.entries(cuerpo as Record<string, unknown>)) {
      const texto = Array.isArray(valor) ? String(valor[0]) : typeof valor === 'string' ? valor : null;
      if (texto) salida[(campo in VACIO || campo === 'correos_autorizados' ? campo : 'general') as keyof Errores] = texto;
    }
  }
  return salida;
}

/**
 * HU-53 (CC-22): la empresa cliente solicita un convenio sin crear cuenta (empresas sin el módulo de cuentas). Queda
 * en revisión; el administrador o el despachador la aprueban o rechazan y el resultado llega al correo de contacto.
 */
export function SolicitudConvenio() {
  const { api, empresa, slug } = useContextoPortal();
  const [datos, setDatos] = useState<Datos>(VACIO);
  const [errores, setErrores] = useState<Errores>({});

  useEffect(() => {
    document.title = `Solicitar un convenio · ${empresa.razon_social}`;
  }, [empresa.razon_social]);

  const enviar = useMutation({
    mutationFn: () =>
      resultado(
        api.POST('/api/portal/{slug}/convenio/', {
          params: { path: { slug } },
          body: {
            cliente_nombre: datos.cliente_nombre.trim(),
            cliente_rut: datos.cliente_rut.trim(),
            direccion: datos.direccion.trim(),
            contacto_nombre: datos.contacto_nombre.trim(),
            contacto_correo: datos.contacto_correo.trim(),
            contacto_telefono: datos.contacto_telefono.trim(),
            viajes_estimados_mes: Number(datos.viajes_estimados_mes),
            correos_autorizados: datos.correos.split(/[\s,;]+/).filter(Boolean),
            sitio_web: datos.sitio_web,
          },
        }),
      ),
    onError: (error) => {
      if (error instanceof ErrorApi && error.estado === 400) setErrores(primerError(error.cuerpo));
      else if (error instanceof ErrorApi && error.estado === 429) setErrores({ general: 'Enviaste varias solicitudes seguidas. Espera un rato.' });
      else setErrores({ general: 'No pudimos enviar la solicitud. Intenta de nuevo.' });
    },
  });

  function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados: Errores = {};
    for (const campo of Object.keys(ETIQUETAS) as (keyof typeof ETIQUETAS)[]) {
      if (!datos[campo].trim()) encontrados[campo] = `Completa «${ETIQUETAS[campo]}».`;
    }
    const viajes = Number(datos.viajes_estimados_mes);
    if (datos.viajes_estimados_mes && (!Number.isInteger(viajes) || viajes < 1)) encontrados.viajes_estimados_mes = 'Indica un número de viajes mayor que cero.';
    setErrores(encontrados);
    if (Object.keys(encontrados).length === 0) enviar.mutate();
  }

  if (enviar.isSuccess) {
    return (
      <section className={e.paginaAngosta} aria-labelledby="titulo-recibida">
        <h1 id="titulo-recibida" className={e.tituloPagina}>
          Solicitud recibida
        </h1>
        <p className={e.subtituloPagina}>
          {empresa.razon_social} revisará tu solicitud de convenio y te avisará por correo a <strong>{datos.contacto_correo.trim()}</strong>.
        </p>
      </section>
    );
  }

  const campo = (nombre: keyof typeof ETIQUETAS, extra: Partial<Parameters<typeof Campo>[0]> = {}) => (
    <Campo
      etiqueta={ETIQUETAS[nombre]}
      value={datos[nombre]}
      error={errores[nombre]}
      onChange={(ev) => setDatos((d) => ({ ...d, [nombre]: ev.target.value }))}
      {...extra}
    />
  );

  return (
    <section className={e.paginaAngosta} aria-labelledby="titulo-convenio">
      <h1 id="titulo-convenio" className={e.tituloPagina}>
        Solicita un convenio
      </h1>
      <p className={e.subtituloPagina}>
        Para empresas que viajan seguido. Al aprobarse, el correo de contacto recibe la clave del convenio: con ella piden traslados el contacto y
        los correos autorizados.
      </p>
      <form className={e.formulario} onSubmit={alEnviar} noValidate aria-label="Solicitud de convenio">
        {errores.general && <Aviso tipo="error">{errores.general}</Aviso>}
        {campo('cliente_nombre', { autoComplete: 'organization' })}
        {campo('cliente_rut', { placeholder: '12345678-9' })}
        {campo('direccion', { autoComplete: 'street-address' })}
        {campo('contacto_nombre', { autoComplete: 'name' })}
        {campo('contacto_correo', { type: 'email', autoComplete: 'email', ayuda: 'Aquí llegan el resultado y, si se aprueba, la clave del convenio.' })}
        {campo('contacto_telefono', { type: 'tel', autoComplete: 'tel', placeholder: '+56912345678' })}
        {campo('viajes_estimados_mes', { type: 'number', inputMode: 'numeric', min: 1 })}
        <Campo
          etiqueta="Correos autorizados para pedir viajes"
          value={datos.correos}
          error={errores.correos_autorizados}
          ayuda="Quienes, además del contacto, pueden pedir con la clave. Separados por coma; «@tuempresa.cl» autoriza todo el dominio."
          onChange={(ev) => setDatos((d) => ({ ...d, correos: ev.target.value }))}
        />
        {/* Campo trampa: oculto para las personas; un bot lo llena. */}
        <div aria-hidden="true" style={{ position: 'absolute', left: '-10000px' }}>
          <label>
            Sitio web
            <input tabIndex={-1} autoComplete="off" value={datos.sitio_web} onChange={(ev) => setDatos((d) => ({ ...d, sitio_web: ev.target.value }))} />
          </label>
        </div>
        <Boton type="submit" ancho cargando={enviar.isPending}>
          {enviar.isPending ? 'Enviando…' : 'Enviar solicitud'}
        </Boton>
      </form>
    </section>
  );
}
