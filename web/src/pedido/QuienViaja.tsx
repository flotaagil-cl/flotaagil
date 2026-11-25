import { Link } from 'react-router';
import { Casilla } from '../diseno/Campo';
import { Contador } from '../diseno/Contador';
import e from '../diseno/diseno.module.css';
import { Segmentado } from '../diseno/Segmentado';
import { PERSONA_VACIA, totalPersonas, type DatosConvenio, type ErroresConvenio, type Para, type Vehiculos } from '../portal/convenio';
import { DatosPersona } from '../portal/PersonasConvenio';

interface Props {
  slug: string;
  datos: DatosConvenio;
  errores: ErroresConvenio;
  /** DC-43: personas en un vehículo. */
  capacidad: number;
  /** Personas por solicitud en vehículos separados. */
  tope: number;
  onCambiar: (datos: DatosConvenio) => void;
}

/**
 * CC-26 (HU-76): quién viaja, dentro del formulario «Pedir traslado» del pasajero con cuenta (sin paso nuevo).
 * Para mí o para otra persona; con más de un pasajero, los acompañantes en el mismo vehículo o en vehículos
 * separados (un viaje por persona). Con una sola persona y «Para mí», el pedido es el de siempre. Reutiliza el
 * modelo de CC-23 y CC-25 (`portal/convenio.ts`), sin cargo ni correo.
 */
export function QuienViaja({ slug, datos, errores, capacidad, tope, onCambiar }: Props) {
  const cambiar = <K extends keyof DatosConvenio>(campo: K, valor: DatosConvenio[K]) => onCambiar({ ...datos, [campo]: valor });
  const separados = datos.vehiculos === 'SEPARADOS';
  const total = totalPersonas(datos);
  const pasajeros = (n: number) => {
    const lista = datos.acompanantes.slice(0, n - 1);
    while (lista.length < n - 1) lista.push(PERSONA_VACIA);
    onCambiar({ ...datos, acompanado: n > 1, acompanantes: lista });
  };
  const vehiculos = (valor: Vehiculos) => {
    // Al volver al mismo vehículo se recortan los acompañantes que no caben.
    const lista = valor === 'MISMO' ? datos.acompanantes.slice(0, Math.max(0, capacidad - 1)) : datos.acompanantes;
    onCambiar({ ...datos, vehiculos: valor, acompanantes: lista, acompanado: lista.length > 0 });
  };
  return (
    <>
      <Segmentado<Para>
        etiqueta="¿Para quién es?"
        forma="pastillas"
        opciones={[
          { valor: 'MI', texto: 'Para mí' },
          { valor: 'OTRO', texto: 'Para otra persona' },
        ]}
        valor={datos.para}
        onCambiar={(valor) => cambiar('para', valor)}
      />
      {datos.para === 'OTRO' && (
        <DatosPersona
          titulo="Quién viaja"
          persona={datos.pasajero}
          prefijo="pasajero"
          errores={errores}
          telefonoObligatorio
          conCargo={false}
          onCambiar={(persona) => cambiar('pasajero', persona)}
        />
      )}
      <Contador
        etiqueta="Pasajeros"
        unidad="un pasajero"
        valor={total}
        min={1}
        max={Math.max(separados ? tope : capacidad, total)}
        error={errores.acompanantes}
        onCambiar={pasajeros}
      />
      {total > 1 && (
        <>
          <Segmentado<Vehiculos>
            etiqueta="¿Cómo viajan?"
            forma="pastillas"
            opciones={[
              { valor: 'MISMO', texto: 'Mismo vehículo' },
              { valor: 'SEPARADOS', texto: 'Vehículos separados' },
            ]}
            valor={datos.vehiculos}
            onCambiar={vehiculos}
          />
          <p className={e.ayuda}>
            {separados
              ? `Un vehículo por persona, con el mismo origen, destino y hora (hasta ${tope} personas).`
              : `En un vehículo caben ${capacidad} personas en total.`}
          </p>
          {datos.acompanantes.map((acompanante, i) => (
            <DatosPersona
              // El orden es la identidad: la lista solo crece o se acorta por el final.
              key={i}
              titulo={`Acompañante ${i + 1}`}
              persona={acompanante}
              prefijo={`acompanantes.${i}`}
              errores={errores}
              telefonoObligatorio={separados}
              conCargo={false}
              onCambiar={(persona) => cambiar('acompanantes', datos.acompanantes.map((a, j) => (j === i ? persona : a)))}
            />
          ))}
        </>
      )}
      {(datos.para === 'OTRO' || total > 1) && (
        <Casilla checked={datos.declara_informados} error={errores.declara_informados} onChange={(ev) => cambiar('declara_informados', ev.target.checked)}>
          Declaro que informé a las personas que viajan sobre el{' '}
          <Link to={`/solicitar/${slug}/privacidad`} target="_blank">
            aviso de privacidad
          </Link>
          .
        </Casilla>
      )}
    </>
  );
}
