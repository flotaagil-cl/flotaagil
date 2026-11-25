/**
 * CC-27 (HU-78) y CC-21: apariencia de la empresa, solo del administrador. Paleta del catálogo fijo, logo, nombre de
 * marca e iniciales, con vista previa de panel, portal y app. Al guardar, el panel toma el tema sin recargar (la
 * sesión lleva la apariencia).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useId, useMemo, useState, type ChangeEvent, type FormEvent } from 'react';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import panel from '../componentes/panel.module.css';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import type { Apariencia as Datos } from '../diseno/LogoEmpresa';
import { nombreVisible } from '../diseno/marca';
import { PALETA_PREDETERMINADA, PALETAS, type ClavePaleta } from '../diseno/paletas.generado';
import { FallaDeCarga } from '../flota/componentes/comunes';
import { useApi, useSesion } from '../sesion/SesionProvider';
import c from './apariencia.module.css';
import { inicialesValidas, limpiarNombre, MAXIMO_NOMBRE, revisarArchivo, TIPOS } from './archivo';
import { VistaPrevia } from './VistaPrevia';

function mensajeDe(error: unknown): string {
  const cuerpo = error instanceof ErrorApi && error.cuerpo && typeof error.cuerpo === 'object' ? (error.cuerpo as Record<string, unknown>) : {};
  const primero = Object.values(cuerpo).find((v) => Array.isArray(v)) as string[] | undefined;
  return primero?.[0] ?? 'No se pudo guardar. Intenta de nuevo.';
}

export function Apariencia() {
  const api = useApi();
  const consulta = useQuery({ queryKey: ['apariencia'], queryFn: () => resultado(api.GET('/api/apariencia/')) });
  return (
    <section>
      <div className={panel.encabezado}>
        <h1>Apariencia</h1>
      </div>
      <p className={panel.explicacion}>
        La marca de tu empresa se ve en el panel, el portal del pasajero, la app del conductor y los correos. Cada cambio queda en la auditoría.
      </p>
      {consulta.isPending ? (
        <Cargando />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="la apariencia" reintentar={() => void consulta.refetch()} />
      ) : (
        <Formulario actual={consulta.data} />
      )}
    </section>
  );
}

/** Vista local del archivo elegido, antes de subirlo. */
function useVistaDeArchivo(archivo: File | null): string | null {
  const url = useMemo(() => (archivo && typeof URL.createObjectURL === 'function' ? URL.createObjectURL(archivo) : null), [archivo]);
  useEffect(() => {
    return () => {
      if (url) URL.revokeObjectURL?.(url);
    };
  }, [url]);
  return url;
}

function Formulario({ actual }: { actual: Datos }) {
  const api = useApi();
  const consultas = useQueryClient();
  const { sesion, estado } = useSesion();
  const [paleta, setPaleta] = useState<ClavePaleta>(actual.paleta);
  const [nombre, setNombre] = useState(actual.nombre_marca);
  const [iniciales, setIniciales] = useState(actual.iniciales);
  const [archivo, setArchivo] = useState<File | null>(null);
  const [errorLogo, setErrorLogo] = useState<string | null>(null);
  const [falla, setFalla] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  const [vuelta, setVuelta] = useState(0); // reinicia el campo de archivo
  const idArchivo = useId();
  const vista = useVistaDeArchivo(archivo);
  const empresa = estado.fase === 'autenticada' ? estado.usuario.empresa : null;

  function aplicar(datos: Datos, mensaje: string) {
    consultas.setQueryData(['apariencia'], datos);
    // El panel toma el tema nuevo sin recargar.
    if (empresa) sesion.actualizarUsuario({ empresa: { ...empresa, apariencia: datos } });
    setAviso(mensaje);
  }

  const guardar = useMutation({
    mutationFn: async (cambios: { paleta?: ClavePaleta; nombre?: string; iniciales?: string; archivo?: File | null }) => {
      let datos = actual;
      if (cambios.archivo) {
        const formulario = new FormData();
        formulario.append('logo', cambios.archivo);
        datos = await resultado(api.POST('/api/apariencia/logo/', { body: {} as never, bodySerializer: () => formulario }));
        setArchivo(null);
        setVuelta((v) => v + 1);
      }
      // Solo se envía lo que cambia.
      const cuerpo = {
        ...(cambios.paleta && cambios.paleta !== datos.paleta && { paleta: cambios.paleta }),
        ...(cambios.nombre !== undefined && cambios.nombre !== datos.nombre_marca && { nombre_marca: cambios.nombre }),
        ...(cambios.iniciales !== undefined && cambios.iniciales !== datos.iniciales && { iniciales: cambios.iniciales }),
      };
      if (Object.keys(cuerpo).length > 0) {
        datos = await resultado(api.PATCH('/api/apariencia/', { body: cuerpo }));
      }
      return datos;
    },
    onSuccess: (datos, cambios) => {
      setPaleta(datos.paleta);
      // «Restablecer» solo toca la paleta: no borra lo que se esté escribiendo.
      if (cambios.nombre !== undefined) setNombre(datos.nombre_marca);
      if (cambios.iniciales !== undefined) setIniciales(datos.iniciales);
      aplicar(datos, 'Cambios guardados.');
    },
    onError: (error) => {
      setFalla(mensajeDe(error));
      void consultas.invalidateQueries({ queryKey: ['apariencia'] });
    },
  });
  const quitar = useMutation({
    mutationFn: () => resultado(api.DELETE('/api/apariencia/logo/')),
    onSuccess: (datos) => aplicar(datos, datos.iniciales ? 'Se quitó el logo: se muestran las iniciales.' : 'Se quitó el logo: se usa el de FlotaÁgil.'),
    onError: (error) => setFalla(mensajeDe(error)),
  });

  function limpiarAvisos() {
    setAviso(null);
    setFalla(null);
  }

  function elegirArchivo(evento: ChangeEvent<HTMLInputElement>) {
    limpiarAvisos();
    const elegido = evento.target.files?.[0] ?? null;
    const error = elegido ? revisarArchivo(elegido) : null;
    setErrorLogo(error);
    setArchivo(error ? null : elegido);
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    limpiarAvisos();
    if (!inicialesOk) return;
    guardar.mutate({ paleta, nombre: nombreLimpio, iniciales, archivo });
  }

  const ocupado = guardar.isPending || quitar.isPending;
  const nombreLimpio = limpiarNombre(nombre);
  const inicialesOk = inicialesValidas(iniciales);
  const hayCambios = paleta !== actual.paleta || archivo !== null || nombreLimpio !== actual.nombre_marca || iniciales !== actual.iniciales;
  const razonSocial = empresa?.razon_social ?? 'Tu empresa';
  const logoVisible = vista ?? actual.logo?.panel ?? null;

  return (
    <form className={c.formulario} onSubmit={enviar} noValidate>
      <fieldset className={panel.tarjeta}>
        <legend>Paleta de colores</legend>
        <div className={c.paletas}>
          {PALETAS.map((opcion) => (
            <label key={opcion.clave} className={c.paleta} data-paleta={opcion.clave}>
              <input
                type="radio"
                name="paleta"
                value={opcion.clave}
                checked={paleta === opcion.clave}
                onChange={() => {
                  limpiarAvisos();
                  setPaleta(opcion.clave);
                }}
              />
              <span className={c.muestra} aria-hidden="true">
                <span className={c.claro} />
              </span>
              <span className={c.nombre}>
                {opcion.nombre}
                {opcion.clave === PALETA_PREDETERMINADA && <span className={c.predeterminada}> (predeterminada)</span>}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className={panel.tarjeta}>
        <legend>Logo de la empresa</legend>
        <p className={panel.explicacion} id={`${idArchivo}-ayuda`}>
          PNG, JPG o WebP, hasta 2 MB y al menos 256 px de ancho. Se recortan los márgenes vacíos. SVG no se acepta.
        </p>
        <div className={c.logo}>
          <div className={c.marco}>
            {logoVisible ? (
              <img src={logoVisible} alt={vista ? 'Vista previa del logo nuevo' : 'Logo actual'} />
            ) : (
              <span className={c.sinLogo}>
                {actual.iniciales ? `Sin logo propio: se muestran las iniciales ${actual.iniciales}.` : 'Sin logo propio: se usa el de FlotaÁgil.'}
              </span>
            )}
          </div>
          <div className={c.acciones}>
            <label className={c.archivo} htmlFor={idArchivo}>
              {actual.logo ? 'Reemplazar el logo' : 'Subir un logo'}
            </label>
            <input key={vuelta} id={idArchivo} type="file" accept={TIPOS.join(',')} aria-describedby={`${idArchivo}-ayuda`} onChange={elegirArchivo} />
            {actual.logo && (
              <button
                type="button"
                className={panel.botonSecundario}
                disabled={ocupado}
                onClick={() => {
                  limpiarAvisos();
                  quitar.mutate();
                }}
              >
                Quitar el logo
              </button>
            )}
          </div>
        </div>
        {errorLogo && <Aviso tipo="error">{errorLogo}</Aviso>}
      </fieldset>

      <fieldset className={panel.tarjeta}>
        <legend>Nombre de marca e iniciales</legend>
        <div className={c.datos}>
          <Campo
            etiqueta="Nombre de marca"
            maxLength={MAXIMO_NOMBRE}
            placeholder={razonSocial}
            autoComplete="off"
            value={nombre}
            ayuda="Opcional, hasta 30 caracteres. Si queda vacío se muestra la razón social."
            onChange={(evento) => {
              limpiarAvisos();
              setNombre(evento.target.value);
            }}
          />
          <Campo
            etiqueta="Iniciales"
            maxLength={3}
            autoComplete="off"
            value={iniciales}
            ayuda="Opcionales, de 1 a 3 letras o números. Se muestran cuando no hay logo."
            error={inicialesOk ? undefined : 'Usa solo letras o números, sin espacios ni signos.'}
            onChange={(evento) => {
              limpiarAvisos();
              setIniciales(evento.target.value.toUpperCase());
            }}
          />
        </div>
      </fieldset>

      <section className={panel.tarjeta} aria-labelledby="titulo-vista">
        <h2 id="titulo-vista">Vista previa</h2>
        <VistaPrevia paleta={paleta} logo={vista ?? actual.logo?.portal ?? null} iniciales={iniciales} empresa={nombreVisible({ nombre_marca: nombreLimpio }, razonSocial)} />
      </section>

      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {aviso && <Aviso>{aviso}</Aviso>}
      <div className={panel.acciones}>
        <Boton type="submit" cargando={guardar.isPending} disabled={!hayCambios || !inicialesOk || ocupado}>
          Guardar cambios
        </Boton>
        <button
          type="button"
          className={panel.botonSecundario}
          disabled={ocupado || (actual.paleta === PALETA_PREDETERMINADA && paleta === PALETA_PREDETERMINADA)}
          onClick={() => {
            limpiarAvisos();
            setPaleta(PALETA_PREDETERMINADA);
            guardar.mutate({ paleta: PALETA_PREDETERMINADA });
          }}
        >
          Restablecer a Tiffany
        </button>
      </div>
    </form>
  );
}
