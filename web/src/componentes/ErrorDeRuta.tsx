import { useLocation, useRouteError } from 'react-router';
import { esRutaDelPortal } from './central';
import { ContactoDeError } from './ContactoDeError';
import estilos from './SinConexion.module.css';

/** El chunk de una pantalla no se pudo descargar: típico tras un despliegue (los nombres con hash cambian). */
export function esFallaDeCarga(error: unknown): boolean {
  return (
    error instanceof TypeError &&
    /dynamically imported module|module script|Importing a module|Failed to fetch/i.test(error.message)
  );
}

export function ErrorDeRuta() {
  const error = useRouteError();
  const carga = esFallaDeCarga(error);
  // HU-49: en el portal no hay «panel» ni «administrador»: se habla de la página y de la central.
  const portal = esRutaDelPortal(useLocation().pathname);
  return (
    <main className={estilos.pagina}>
      <section className={estilos.tarjeta} role="alert">
        <h1>{carga ? `Hay una versión nueva ${portal ? 'de la página' : 'del panel'}` : 'Ocurrió un error inesperado'}</h1>
        <p>
          {carga
            ? 'No se pudo cargar esta pantalla. Recarga para usar la versión actual.'
            : `Recarga la página. Si el problema sigue, ${portal ? 'contacta a la central' : 'avisa al administrador'}.`}
        </p>
        <button type="button" className={estilos.boton} onClick={() => window.location.reload()}>
          Recargar
        </button>
        {!carga && <ContactoDeError />}
      </section>
    </main>
  );
}
