import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './diseno/tokens.css';
import './estilos.css';

// HU-59 (CC-20, DC-58): el tema común del sistema visual en toda la app.
document.body.classList.add('tema-flotaagil');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
