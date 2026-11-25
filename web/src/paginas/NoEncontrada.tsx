import { Link } from 'react-router';
import { useTitulo } from '../diseno/titulo';

export function NoEncontrada() {
  useTitulo('Página no encontrada');
  return (
    <main style={{ padding: 'var(--espacio-4)' }}>
      <h1>Página no encontrada</h1>
      <p>
        <Link to="/">Ir al inicio</Link>
      </p>
    </main>
  );
}
