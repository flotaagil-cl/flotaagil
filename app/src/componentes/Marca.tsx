import { useTema } from '../tema/useTema';
import { Icono } from './Icono';

/** CC-27 y CC-21: el logo de la empresa; sin logo, sus iniciales y, si no hay, la marca de FlotaÁgil (el auto). */
export function Marca({ clase, tamano }: { clase: 'barra-logo' | 'login-logo'; tamano: number }) {
  const tema = useTema();
  if (tema?.logo) return <img className={`logo-empresa ${clase}`} src={tema.logo} alt={`Logo de ${tema.empresa}`} />;
  if (tema?.iniciales) {
    return (
      <div className={`${clase} marca-iniciales`} role="img" aria-label={`Iniciales de ${tema.empresa}`}>
        {tema.iniciales}
      </div>
    );
  }
  return (
    <div className={clase} aria-hidden="true">
      <Icono nombre="auto" tamano={tamano} />
    </div>
  );
}
