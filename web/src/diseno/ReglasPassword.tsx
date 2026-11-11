import e from './diseno.module.css';
import { Icono } from './Icono';

/** Lista de reglas con su estado en texto (para lectores de pantalla) y un ícono verde al cumplirse. */
export function ReglasPassword({ reglas, id }: { reglas: { texto: string; cumple: boolean }[]; id?: string }) {
  return (
    <ul className={e.reglas} id={id} aria-label="Requisitos de la contraseña">
      {reglas.map((regla) => (
        <li key={regla.texto} data-cumple={regla.cumple}>
          <span className={e.reglaMarca} aria-hidden="true">
            <Icono nombre="check" tamano={12} />
          </span>
          {regla.texto}
          <span className="solo-lector">{regla.cumple ? ' (cumple)' : ' (pendiente)'}</span>
        </li>
      ))}
    </ul>
  );
}
