import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { Aviso } from '../componentes/Aviso';
import estilos from '../componentes/panel.module.css';
import campos from '../formularios/formularios.module.css';
import { normalizarRut, rutValido } from '../flota/formularios';
import { ErrorApi } from '../api/resultado';
import { mensajeDeErrorApi } from '../reservas/errores';

export function DialogoPassword({ password, cliente, alCerrar }: { password: string; cliente: string; alCerrar: () => void }) {
  const dialogo = useRef<HTMLDialogElement>(null);
  const [copiada, setCopiada] = useState<boolean | null>(null);

  useEffect(() => {
    const elemento = dialogo.current;
    if (!elemento || elemento.open) return;
    if (typeof elemento.showModal === 'function') elemento.showModal();
    else elemento.setAttribute('open', '');
    return () => {
      if (typeof elemento.close === 'function') elemento.close();
      else elemento.removeAttribute('open');
    };
  }, []);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(password);
      setCopiada(true);
    } catch {
      setCopiada(false);
    }
  }

  return (
    <dialog
      ref={dialogo}
      className={estilos.dialogo}
      aria-labelledby="titulo-password"
      onCancel={(evento) => {
        evento.preventDefault();
        alCerrar();
      }}
    >
      <div className={estilos.formularioDialogo}>
        <h2 id="titulo-password">Contraseña del convenio</h2>
        <p>
          Entrégasela a <strong>{cliente}</strong> por un canal seguro. No se volverá a mostrar: si se pierde, rota la contraseña.
        </p>
        <p className={estilos.password} aria-label="Contraseña del convenio">
          {password}
        </p>
        {copiada === true && <Aviso>Copiada.</Aviso>}
        {copiada === false && <Aviso tipo="error">No se pudo copiar: selecciónala y cópiala a mano.</Aviso>}
        <div className={estilos.acciones}>
          <button type="button" className={estilos.boton} onClick={() => void copiar()}>
            Copiar
          </button>
          <button type="button" className={estilos.botonSecundario} onClick={alCerrar}>
            Listo
          </button>
        </div>
      </div>
    </dialog>
  );
}

export interface DatosFormulario {
  cliente_nombre: string;
  cliente_rut: string;
}

type Errores = Partial<Record<keyof DatosFormulario, string>>;

function erroresDelServidor(error: unknown): Errores | null {
  if (!(error instanceof ErrorApi) || error.estado !== 400) return null;
  const cuerpo = (error.cuerpo ?? {}) as Record<string, string[] | undefined>;
  const encontrados: Errores = {};
  if (cuerpo.cliente_nombre?.[0]) encontrados.cliente_nombre = cuerpo.cliente_nombre[0];
  if (cuerpo.cliente_rut?.[0]) encontrados.cliente_rut = cuerpo.cliente_rut[0];
  return Object.keys(encontrados).length ? encontrados : null;
}

/** Nombre y RUT del cliente, al crear y al editar. Repite la validación del backend para avisar antes de enviar. */
export function FormularioConvenio({
  iniciales,
  textoEnviar,
  volverA,
  enviar,
}: {
  iniciales: DatosFormulario;
  textoEnviar: string;
  volverA: string;
  enviar: (datos: DatosFormulario) => Promise<void>;
}) {
  const [datos, setDatos] = useState(iniciales);
  const [errores, setErrores] = useState<Errores>({});
  const [falla, setFalla] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function alEnviar(evento: FormEvent) {
    evento.preventDefault();
    const limpio = { cliente_nombre: datos.cliente_nombre.trim(), cliente_rut: normalizarRut(datos.cliente_rut) };
    const nuevos: Errores = {};
    if (!limpio.cliente_nombre) nuevos.cliente_nombre = 'Ingresa el nombre del cliente.';
    if (!rutValido(limpio.cliente_rut)) nuevos.cliente_rut = 'RUT inválido: revisa el número y el dígito verificador.';
    setErrores(nuevos);
    setFalla(null);
    if (Object.keys(nuevos).length) return;
    setEnviando(true);
    try {
      await enviar(limpio);
    } catch (error) {
      const delServidor = erroresDelServidor(error);
      if (delServidor) setErrores(delServidor);
      else setFalla(mensajeDeErrorApi(error));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className={estilos.tarjeta} onSubmit={(evento) => void alEnviar(evento)} noValidate>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      <label className={campos.campo}>
        Cliente
        <input
          value={datos.cliente_nombre}
          maxLength={120}
          aria-invalid={Boolean(errores.cliente_nombre)}
          onChange={(evento) => setDatos({ ...datos, cliente_nombre: evento.target.value })}
        />
        {errores.cliente_nombre && <span role="alert">{errores.cliente_nombre}</span>}
      </label>
      <label className={campos.campo}>
        RUT
        <input
          value={datos.cliente_rut}
          maxLength={14}
          aria-invalid={Boolean(errores.cliente_rut)}
          onChange={(evento) => setDatos({ ...datos, cliente_rut: evento.target.value })}
        />
        {errores.cliente_rut && <span role="alert">{errores.cliente_rut}</span>}
      </label>
      <div className={estilos.acciones}>
        <button type="submit" className={estilos.boton} disabled={enviando}>
          {enviando ? 'Guardando…' : textoEnviar}
        </button>
        <Link to={volverA} className={estilos.botonSecundario}>
          Volver
        </Link>
      </div>
    </form>
  );
}
