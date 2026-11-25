import type { ReactNode } from 'react';
import { Icono } from '../diseno/Icono';
import estilos from './Aviso.module.css';

export function Aviso({ tipo = 'info', children }: { tipo?: 'info' | 'error'; children: ReactNode }) {
  return (
    <p className={`${estilos.aviso} ${estilos[tipo]}`} role={tipo === 'error' ? 'alert' : 'status'}>
      {/* CC-27: ícono y texto; el color no es la única señal. */}
      <Icono nombre={tipo === 'error' ? 'alerta' : 'info'} tamano={16} className={estilos.icono} />
      {children}
    </p>
  );
}
