/**
 * HU-71 (DC-72): campo de dirección con sugerencias (patrón combobox de ARIA). Sugiere desde 3 caracteres, 300 ms
 * después de la última tecla, hasta 5 resultados; se navega con flechas, Enter y Escape. Elegir una guarda el texto
 * y sus coordenadas (el backend no vuelve a geocodificar); escribir a mano las borra. Si el servicio no responde, el
 * campo queda como texto normal, sin errores a la vista.
 */

import { useEffect, useId, useRef, useState, type ComponentProps, type KeyboardEvent, type ReactNode } from 'react';
import c from './direcciones.module.css';
import { ESPERA_MS, MAXIMO, MINIMO_CARACTERES, type Buscar, type Sugerencia } from './sugerencias';

interface Opciones {
  valor: string;
  /** El usuario escribió: el texto nuevo (quien lo usa borra las coordenadas elegidas antes). */
  alCambiar: (texto: string) => void;
  alElegir: (sugerencia: Sugerencia) => void;
  buscar: Buscar;
}

type PropsEntrada = Pick<
  ComponentProps<'input'>,
  'role' | 'value' | 'onChange' | 'onKeyDown' | 'onBlur' | 'autoComplete' | 'aria-autocomplete' | 'aria-expanded' | 'aria-controls' | 'aria-activedescendant'
>;

/** La lógica del combobox, para usarla con cualquiera de los `Campo` (panel o portal). */
export function useCombobox({ valor, alCambiar, alElegir, buscar }: Opciones): { entrada: PropsEntrada; lista: ReactNode } {
  const idLista = useId();
  const [sugerencias, setSugerencias] = useState<Sugerencia[]>([]);
  const [abierta, setAbierta] = useState(false);
  const [activa, setActiva] = useState(-1);
  const [pedido, setPedido] = useState<string | null>(null);
  const buscarRef = useRef(buscar);
  useEffect(() => {
    buscarRef.current = buscar;
  });

  // Espera 300 ms tras la última tecla; cada pedido nuevo cancela el anterior.
  useEffect(() => {
    if (pedido === null) return;
    const texto = pedido.trim();
    if (texto.length < MINIMO_CARACTERES) return;
    const control = new AbortController();
    const reloj = window.setTimeout(() => {
      buscarRef.current(texto, control.signal).then(
        (encontradas) => {
          const visibles = encontradas.slice(0, MAXIMO);
          setSugerencias(visibles);
          setActiva(-1);
          setAbierta(visibles.length > 0);
        },
        () => {
          // Sin servicio: el campo sigue como texto normal.
          setSugerencias([]);
          setAbierta(false);
        },
      );
    }, ESPERA_MS);
    return () => {
      window.clearTimeout(reloj);
      control.abort();
    };
  }, [pedido]);

  function cerrar() {
    setAbierta(false);
    setActiva(-1);
  }

  function elegir(sugerencia: Sugerencia) {
    alElegir(sugerencia);
    setPedido(null);
    setSugerencias([]);
    cerrar();
  }

  function alTeclear(evento: KeyboardEvent<HTMLInputElement>) {
    const hay = sugerencias.length > 0;
    if (evento.key === 'ArrowDown' && hay) {
      evento.preventDefault();
      setAbierta(true);
      setActiva((i) => (i + 1) % sugerencias.length);
    } else if (evento.key === 'ArrowUp' && hay) {
      evento.preventDefault();
      setAbierta(true);
      setActiva((i) => (i <= 0 ? sugerencias.length - 1 : i - 1));
    } else if (evento.key === 'Enter' && abierta && activa >= 0) {
      evento.preventDefault(); // elige; no envía el formulario
      elegir(sugerencias[activa]);
    } else if (evento.key === 'Escape' && abierta) {
      evento.preventDefault();
      cerrar();
    }
  }

  const idOpcion = (i: number) => `${idLista}-${i}`;
  const entrada: PropsEntrada = {
    role: 'combobox',
    value: valor,
    autoComplete: 'off',
    'aria-autocomplete': 'list',
    'aria-expanded': abierta,
    'aria-controls': idLista,
    'aria-activedescendant': abierta && activa >= 0 ? idOpcion(activa) : undefined,
    onChange: (evento) => {
      alCambiar(evento.target.value);
      setPedido(evento.target.value);
      if (evento.target.value.trim().length < MINIMO_CARACTERES) {
        setSugerencias([]);
        cerrar();
      }
    },
    onKeyDown: alTeclear,
    onBlur: cerrar,
  };

  const lista = (
    <div className={c.desplegable} hidden={!abierta}>
      <ul id={idLista} role="listbox" aria-label="Sugerencias de direcciones" className={c.lista}>
        {sugerencias.map((sugerencia, i) => (
          <li
            key={`${sugerencia.texto}-${i}`}
            id={idOpcion(i)}
            role="option"
            aria-selected={i === activa}
            className={c.opcion}
            // mousedown y no click: el campo no pierde el foco antes de elegir.
            onMouseDown={(evento) => {
              evento.preventDefault();
              elegir(sugerencia);
            }}
          >
            {sugerencia.texto}
          </li>
        ))}
      </ul>
      <p className={c.atribucion}>© OpenStreetMap contributors</p>
    </div>
  );

  return { entrada, lista };
}
