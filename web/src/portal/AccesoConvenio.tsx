import { useMutation } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { codigoDe, ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import e from '../diseno/diseno.module.css';
import { Destacado, Tarjeta } from '../diseno/Tarjeta';
import { guardarPase, type PaseConvenio } from './convenio';
import { useContextoPortal } from './contexto';

interface PropsAcceso {
  alEntrar: (pase: PaseConvenio) => void;
  alPedirComoNatural: () => void;
  /** Al volver por un pase vencido o invalidado, se explica por qué. */
  aviso?: string;
}

/** CC-23 (HU-73): paso 1 del modo Empresa con convenio: correo + clave → pase. La clave no se guarda. */
export function AccesoConvenio({ alEntrar, alPedirComoNatural, aviso }: PropsAcceso) {
  const { api, slug } = useContextoPortal();
  const [correo, setCorreo] = useState('');
  const [clave, setClave] = useState('');
  const [errores, setErrores] = useState<{ correo?: string; clave?: string; general?: string }>({});

  const entrar = useMutation({
    mutationFn: () =>
      resultado(api.POST('/api/portal/{slug}/convenio/pase/', { params: { path: { slug } }, body: { correo: correo.trim(), clave } })),
    onSuccess: (pase) => {
      setClave('');
      guardarPase(slug, pase);
      alEntrar(pase);
    },
    onError: (error) => {
      const codigo = codigoDe(error);
      if (codigo === 'clave_bloqueada') setErrores({ general: 'Demasiados intentos con este correo. Espera unos minutos e intenta de nuevo.' });
      else if (error instanceof ErrorApi && error.estado === 429) setErrores({ general: 'Se hicieron demasiados intentos. Espera un rato e intenta de nuevo.' });
      else if (error instanceof ErrorApi && error.estado === 400 && codigo !== 'clave_invalida') setErrores({ correo: 'Revisa el correo.' });
      else if (codigo === 'clave_invalida') setErrores({ general: 'El correo o la clave no son válidos para un convenio vigente.' });
      else setErrores({ general: 'No pudimos revisar la clave. Intenta de nuevo.' });
    },
  });

  const alEnviar = (evento: FormEvent) => {
    evento.preventDefault();
    const encontrados: typeof errores = {};
    if (!/^\S+@\S+\.\S+$/.test(correo.trim())) encontrados.correo = 'Escribe el correo de tu empresa.';
    if (!clave.trim()) encontrados.clave = 'Escribe la clave del convenio.';
    setErrores(encontrados);
    if (Object.keys(encontrados).length === 0) entrar.mutate();
  };

  return (
    <>
      <Tarjeta como="section" aria-labelledby="titulo-clave">
        <form className={e.formulario} onSubmit={alEnviar} noValidate aria-label="Acceso con clave de convenio">
          <div>
            <h2 id="titulo-clave" className={e.resumenTitulo}>
              Entra con la clave de tu convenio
            </h2>
            <p className={e.ayuda}>La recibió el contacto de tu empresa al aprobarse el convenio.</p>
          </div>
          {aviso && <Aviso>{aviso}</Aviso>}
          {errores.general && <Aviso tipo="error">{errores.general}</Aviso>}
          <Campo
            etiqueta="Correo de la empresa"
            type="email"
            autoComplete="email"
            value={correo}
            error={errores.correo}
            ayuda="El contacto del convenio o un correo autorizado."
            onChange={(ev) => setCorreo(ev.target.value)}
          />
          <Campo
            etiqueta="Clave del convenio"
            type="password"
            autoComplete="off"
            spellCheck={false}
            value={clave}
            error={errores.clave}
            onChange={(ev) => setClave(ev.target.value)}
          />
          <Boton type="submit" ancho cargando={entrar.isPending}>
            {entrar.isPending ? 'Revisando…' : 'Continuar'}
          </Boton>
        </form>
      </Tarjeta>
      <p className={e.nota}>
        <Link to={`/solicitar/${slug}/convenio`}>Mi empresa no tiene convenio</Link>
        {' · '}
        <button type="button" className={e.botonEnlace} onClick={alPedirComoNatural}>
          Pedir como pasajero natural
        </button>
      </p>
    </>
  );
}

/** Tarjeta del pase: la empresa y el correo enmascarado, con la opción de salir. */
export function TarjetaPase({ pase, alSalir }: { pase: PaseConvenio; alSalir: () => void }) {
  return (
    <Destacado
      icono="convenios"
      titulo={pase.cliente_nombre}
      accion={
        <button type="button" className={e.destacadoAccion} onClick={alSalir}>
          Salir
        </button>
      }
    >
      Convenio activo · {pase.correo}
    </Destacado>
  );
}
