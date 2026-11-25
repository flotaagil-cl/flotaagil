import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { temaApp } from './tema/instancia';
import './diseno/tokens.css';
import './diseno/paletas.css';
import './estilos.css';

// HU-59 (CC-20, DC-58): el tema común del sistema visual en toda la app.
document.body.classList.add('tema-flotaagil');
// CC-27: la paleta guardada se aplica antes de pintar, también sin conexión.
temaApp.aplicar();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
