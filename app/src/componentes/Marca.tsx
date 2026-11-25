import { useTema } from '../tema/useTema';
import { Icono } from './Icono';

/** CC-27 (HU-80): el logo de la empresa; si no tiene, la marca de FlotaÁgil (el ícono del auto). */
export function Marca({ clase, tamano }: { clase: 'barra-logo' | 'login-logo'; tamano: number }) {
  const tema = useTema();
  if (tema?.logo) return <img className={`logo-empresa ${clase}`} src={tema.logo} alt={`Logo de ${tema.empresa}`} />;
  return (
    <div className={clase} aria-hidden="true">
      <Icono nombre="auto" tamano={tamano} />
    </div>
  );
}
