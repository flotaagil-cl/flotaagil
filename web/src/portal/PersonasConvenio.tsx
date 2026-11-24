import { Campo, Casilla } from '../diseno/Campo';
import { Contador } from '../diseno/Contador';
import e from '../diseno/diseno.module.css';
import { Segmentado } from '../diseno/Segmentado';
import { Tarjeta } from '../diseno/Tarjeta';
import { Link } from 'react-router';
import {
  maximoAcompanantes,
  PERSONA_VACIA,
  type DatosConvenio,
  type ErroresConvenio,
  type Para,
  type Persona,
  type Vehiculos,
} from './convenio';

interface Props {
  slug: string;
  datos: DatosConvenio;
  errores: ErroresConvenio;
  capacidad: number;
  tope: number;
  onCambiar: (datos: DatosConvenio) => void;
}

interface PropsPersona {
  titulo: string;
  persona: Persona;
  prefijo: string;
  errores: ErroresConvenio;
  /** En el mismo vehículo el teléfono de un acompañante es opcional; quien es Pasajero de un viaje, no (D4). */
  telefonoObligatorio: boolean;
  ayudaCorreo: string;
  onCambiar: (persona: Persona) => void;
}

function DatosPersona({ titulo, persona, prefijo, errores, telefonoObligatorio, ayudaCorreo, onCambiar }: PropsPersona) {
  const cambiar = (campo: keyof Persona) => (ev: { target: { value: string } }) => onCambiar({ ...persona, [campo]: ev.target.value });
  return (
    <Tarjeta como="section" className={e.formulario}>
      <h3 className={e.resumenTitulo}>{titulo}</h3>
      <div className={e.filaPersona}>
        <Campo etiqueta="Nombre y apellido" value={persona.nombre} error={errores[`${prefijo}.nombre`]} onChange={cambiar('nombre')} />
        <Campo etiqueta="Cargo" value={persona.cargo} error={errores[`${prefijo}.cargo`]} onChange={cambiar('cargo')} />
        <Campo
          etiqueta={telefonoObligatorio ? 'Teléfono' : 'Teléfono (opcional, medio de contacto)'}
          type="tel"
          value={persona.telefono}
          error={errores[`${prefijo}.telefono`]}
          ayuda={telefonoObligatorio ? 'Solo lo ve la central, nunca el conductor.' : undefined}
          onChange={cambiar('telefono')}
        />
        <Campo etiqueta="Correo (opcional)" type="email" value={persona.correo} error={errores[`${prefijo}.correo`]} ayuda={ayudaCorreo} onChange={cambiar('correo')} />
      </div>
    </Tarjeta>
  );
}

const AYUDA_CORREO = 'Le enviamos los datos del viaje, sin enlace de confirmación.';

/** CC-23 (HU-73): quién viaja en una reserva con pase de convenio (D4, D6, D7). */
export function PersonasConvenio({ slug, datos, errores, capacidad, tope, onCambiar }: Props) {
  const cambiar = <K extends keyof DatosConvenio>(campo: K, valor: DatosConvenio[K]) => onCambiar({ ...datos, [campo]: valor });
  const maximo = maximoAcompanantes(datos, capacidad, tope);
  const cantidad = (n: number) => {
    const lista = datos.acompanantes.slice(0, n);
    while (lista.length < n) lista.push(PERSONA_VACIA);
    cambiar('acompanantes', lista);
  };
  const separados = datos.vehiculos === 'SEPARADOS';
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
          titulo="Pasajero"
          persona={datos.pasajero}
          prefijo="pasajero"
          errores={errores}
          telefonoObligatorio
          ayudaCorreo={AYUDA_CORREO}
          onCambiar={(persona) => cambiar('pasajero', persona)}
        />
      )}
      <Segmentado<'SOLO' | 'ACOMPANADO'>
        etiqueta="¿Viaja alguien más?"
        forma="pastillas"
        opciones={[
          { valor: 'SOLO', texto: 'Solo' },
          { valor: 'ACOMPANADO', texto: 'Acompañado' },
        ]}
        valor={datos.acompanado ? 'ACOMPANADO' : 'SOLO'}
        onCambiar={(valor) =>
          onCambiar({
            ...datos,
            acompanado: valor === 'ACOMPANADO',
            acompanantes: valor === 'ACOMPANADO' && datos.acompanantes.length === 0 ? [PERSONA_VACIA] : datos.acompanantes,
          })
        }
      />
      {datos.acompanado && (
        <>
          <Segmentado<Vehiculos>
            etiqueta="¿Cómo viajan?"
            forma="pastillas"
            opciones={[
              { valor: 'MISMO', texto: 'Mismo vehículo' },
              { valor: 'SEPARADOS', texto: 'Vehículos separados' },
            ]}
            valor={datos.vehiculos}
            onCambiar={(valor) => cambiar('vehiculos', valor)}
          />
          <p className={e.ayuda}>
            {separados
              ? 'Un vehículo por persona, con el mismo origen, destino y hora. Un solo correo confirma todos los viajes.'
              : `En un vehículo caben ${capacidad} personas en total.`}
          </p>
          <Contador
            etiqueta="Acompañantes"
            unidad="un acompañante"
            valor={datos.acompanantes.length}
            min={1}
            max={Math.max(maximo, datos.acompanantes.length)}
            error={errores.acompanantes}
            onCambiar={cantidad}
          />
          {datos.acompanantes.map((acompanante, i) => (
            <DatosPersona
              // El orden es la identidad: la lista solo crece o se acorta por el final.
              key={i}
              titulo={`Acompañante ${i + 1}`}
              persona={acompanante}
              prefijo={`acompanantes.${i}`}
              errores={errores}
              telefonoObligatorio={separados}
              ayudaCorreo={AYUDA_CORREO}
              onCambiar={(persona) => cambiar('acompanantes', datos.acompanantes.map((a, j) => (j === i ? persona : a)))}
            />
          ))}
        </>
      )}
      {(datos.para === 'OTRO' || datos.acompanado) && (
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
