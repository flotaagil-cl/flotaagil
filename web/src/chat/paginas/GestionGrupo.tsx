import { useState, type FormEvent } from 'react';
import { Aviso } from '../../componentes/Aviso';
import { Cargando } from '../../componentes/Cargando';
import { Boton } from '../../diseno/Boton';
import { Campo } from '../../diseno/Campo';
import { Dialogo } from '../../diseno/Dialogo';
import { useSesion } from '../../sesion/SesionProvider';
import { mensajeDelChat, useGestionGrupo, useGrupo, usePersonal } from '../api';
import c from '../chat.module.css';

interface Props {
  id: number;
  abierto: boolean;
  cerrar: () => void;
  /** Solo los integrantes agregan personas; el administrador que modera sin estar no puede (DC-64). */
  puedeAgregar: boolean;
  puedeBorrar: boolean;
  /** Al salir del grupo o borrarlo. */
  alSalir?: () => void;
}

/** HU-62: renombrar, integrantes y borrado. El backend decide quién puede qué; aquí se muestran sus respuestas. */
export function GestionGrupo({ id, abierto, cerrar, puedeAgregar, puedeBorrar, alSalir }: Props) {
  const grupo = useGrupo(abierto ? id : null);
  const personal = usePersonal(abierto && puedeAgregar);
  const gestion = useGestionGrupo(id);
  const { estado } = useSesion();
  const yo = estado.fase === 'autenticada' ? estado.usuario.id : null;
  const [nombre, setNombre] = useState<string | null>(null);
  const [nuevo, setNuevo] = useState('');
  const [confirmarBorrado, setConfirmarBorrado] = useState(false);
  const [falla, setFalla] = useState<string | null>(null);

  async function intentar(accion: () => Promise<unknown>, despues?: () => void) {
    setFalla(null);
    try {
      await accion();
      despues?.();
    } catch (error) {
      setFalla(mensajeDelChat(error));
    }
  }

  function renombrar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (nombre?.trim()) void intentar(() => gestion.renombrar.mutateAsync(nombre.trim()), () => setNombre(null));
  }

  const datos = grupo.data;
  const integrantes = new Set(datos?.integrantes.map((i) => i.id));
  const disponibles = (personal.data ?? []).filter((p) => !integrantes.has(p.id));

  return (
    <Dialogo abierto={abierto} titulo="Gestionar grupo" onCerrar={cerrar}>
      {falla && <Aviso tipo="error">{falla}</Aviso>}
      {!datos ? (
        <Cargando />
      ) : (
        <>
          <form onSubmit={renombrar} noValidate>
            <Campo etiqueta="Nombre del grupo" maxLength={60} value={nombre ?? datos.nombre} onChange={(e) => setNombre(e.target.value)} />
            <Boton type="submit" variante="secundario" cargando={gestion.renombrar.isPending} disabled={nombre === null}>
              Guardar nombre
            </Boton>
          </form>
          <h3>Integrantes</h3>
          <ul className={c.personas} aria-label="Integrantes">
            {datos.integrantes.map((integrante) => (
              <li key={integrante.id} className={c.integrante}>
                <span>{integrante.nombre}</span>
                <Boton
                  variante="texto"
                  disabled={gestion.quitar.isPending}
                  onClick={() => void intentar(() => gestion.quitar.mutateAsync(integrante.id), integrante.id === yo ? alSalir : undefined)}
                >
                  {integrante.id === yo ? 'Salir del grupo' : `Quitar a ${integrante.nombre}`}
                </Boton>
              </li>
            ))}
          </ul>
          {puedeAgregar && disponibles.length > 0 && (
            <div className={c.agregar}>
              <label>
                Agregar a
                <select value={nuevo} onChange={(e) => setNuevo(e.target.value)}>
                  <option value="">Elige a una persona</option>
                  {disponibles.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre}
                    </option>
                  ))}
                </select>
              </label>
              <Boton variante="secundario" disabled={!nuevo} cargando={gestion.agregar.isPending} onClick={() => void intentar(() => gestion.agregar.mutateAsync(Number(nuevo)), () => setNuevo(''))}>
                Agregar
              </Boton>
            </div>
          )}
          {puedeBorrar && (
            <Boton
              variante="peligro"
              cargando={gestion.borrar.isPending}
              onClick={() => (confirmarBorrado ? void intentar(() => gestion.borrar.mutateAsync(), () => (cerrar(), alSalir?.())) : setConfirmarBorrado(true))}
            >
              {confirmarBorrado ? 'Confirmar: borrar el grupo' : 'Borrar grupo'}
            </Boton>
          )}
        </>
      )}
    </Dialogo>
  );
}
