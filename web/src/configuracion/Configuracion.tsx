/**
 * Configuración de la empresa (DC-68): solo el administrador. Números de la central para los botones de
 * emergencia del portal y parámetros de la reserva pública, con mínimos y máximos; cada cambio queda auditado.
 * El módulo de cuentas no se cambia aquí: es del superusuario.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import type { components } from '../api/esquema';
import { ErrorApi, resultado } from '../api/resultado';
import { Aviso } from '../componentes/Aviso';
import { Cargando } from '../componentes/Cargando';
import estilos from '../componentes/panel.module.css';
import { Boton } from '../diseno/Boton';
import { Campo } from '../diseno/Campo';
import { FallaDeCarga } from '../flota/componentes/comunes';
import { useApi } from '../sesion/SesionProvider';
import c from './configuracion.module.css';

type Datos = components['schemas']['ConfiguracionEmpresa'];
type Numerico = Exclude<keyof Datos, 'telefono_central' | 'whatsapp_central'>;

const NUMEROS: { campo: Numerico; etiqueta: string; min: number; max: number; ayuda: string }[] = [
  { campo: 'confirmacion_antes_horas', etiqueta: 'Plazo para confirmar (horas antes de la recogida)', min: 1, max: 168, ayuda: 'La reserva pública se confirma por correo hasta esas horas antes.' },
  { campo: 'confirmacion_plazo_corto_min', etiqueta: 'Plazo corto (minutos)', min: 10, max: 240, ayuda: 'Si al pedir falta menos que el plazo anterior.' },
  { campo: 'cierre_no_confirmada_horas', etiqueta: 'Cierre de las «Sin confirmar» (horas tras la recogida)', min: 1, max: 48, ayuda: 'Después se cierran solas.' },
  { campo: 'reserva_publica_max_ip_hora', etiqueta: 'Solicitudes por conexión (IP) y hora', min: 5, max: 500, ayuda: 'Antispam del formulario público.' },
  { campo: 'reserva_publica_max_correo_hora', etiqueta: 'Solicitudes por correo y hora', min: 1, max: 50, ayuda: 'Antispam del formulario público.' },
  { campo: 'reserva_publica_max_convenio_hora', etiqueta: 'Solicitudes por correo de convenio y hora', min: 1, max: 500, ayuda: 'Para los correos autorizados de un convenio.' },
];

export function Configuracion() {
  const api = useApi();
  const consulta = useQuery({ queryKey: ['configuracion-empresa'], queryFn: () => resultado(api.GET('/api/configuracion-empresa/')) });
  return (
    <section>
      <div className={estilos.encabezado}>
        <h1>Configuración de la empresa</h1>
      </div>
      <p className={estilos.explicacion}>Cada cambio queda registrado en la auditoría. El módulo de cuentas lo activa el equipo de FlotaÁgil.</p>
      {consulta.isPending ? (
        <Cargando />
      ) : consulta.isError ? (
        <FallaDeCarga error={consulta.error} que="la configuración" reintentar={() => void consulta.refetch()} />
      ) : (
        <Formulario inicial={consulta.data} />
      )}
    </section>
  );
}

function Formulario({ inicial }: { inicial: Datos }) {
  const api = useApi();
  const consultas = useQueryClient();
  const [datos, setDatos] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(inicial).map(([campo, valor]) => [campo, String(valor ?? '')])),
  );
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [guardado, setGuardado] = useState(false);
  const guardar = useMutation({
    mutationFn: (cuerpo: Partial<Datos>) => resultado(api.PATCH('/api/configuracion-empresa/', { body: cuerpo })),
    onSuccess: (nuevos) => {
      consultas.setQueryData(['configuracion-empresa'], nuevos);
      setGuardado(true);
    },
    onError: (error) => {
      const cuerpo = error instanceof ErrorApi && error.cuerpo && typeof error.cuerpo === 'object' ? (error.cuerpo as Record<string, unknown>) : {};
      const porCampo = Object.fromEntries(
        Object.entries(cuerpo)
          .filter(([, valor]) => Array.isArray(valor))
          .map(([campo, valor]) => [campo, String((valor as string[])[0])]),
      );
      setErrores(Object.keys(porCampo).length ? porCampo : { general: 'No se pudo guardar. Intenta de nuevo.' });
    },
  });

  function cambiar(campo: string, valor: string) {
    setDatos((actual) => ({ ...actual, [campo]: valor }));
    setGuardado(false);
  }

  function enviar(evento: FormEvent) {
    evento.preventDefault();
    const encontrados: Record<string, string> = {};
    for (const { campo, min, max } of NUMEROS) {
      const valor = Number(datos[campo]);
      if (!Number.isInteger(valor) || valor < min || valor > max) encontrados[campo] = `Debe ser un número entero entre ${min} y ${max}.`;
    }
    // DC-68: el plazo corto se usa cuando falta menos que el plazo normal, así que debe ser menor que él.
    const horas = Number(datos.confirmacion_antes_horas);
    if (!encontrados.confirmacion_antes_horas && !encontrados.confirmacion_plazo_corto_min && Number(datos.confirmacion_plazo_corto_min) >= horas * 60) {
      encontrados.confirmacion_plazo_corto_min = `Debe ser menor que el plazo para confirmar (${horas} h = ${horas * 60} min).`;
    }
    setErrores(encontrados);
    if (Object.keys(encontrados).length) return;
    guardar.mutate({
      telefono_central: datos.telefono_central.trim(),
      whatsapp_central: datos.whatsapp_central.trim(),
      ...Object.fromEntries(NUMEROS.map(({ campo }) => [campo, Number(datos[campo])])),
    });
  }

  return (
    <form className={c.formulario} onSubmit={enviar} noValidate>
      {errores.general && <Aviso tipo="error">{errores.general}</Aviso>}
      <fieldset className={estilos.tarjeta}>
        <legend>Contacto de emergencia del portal</legend>
        <p className={estilos.explicacion}>Vacío, el botón no se muestra al pasajero.</p>
        <div className={c.grilla}>
          <Campo etiqueta="Teléfono de la central" type="tel" placeholder="+56 2 2999 0000" value={datos.telefono_central} error={errores.telefono_central} onChange={(e) => cambiar('telefono_central', e.target.value)} />
          <Campo etiqueta="WhatsApp de la central" type="tel" placeholder="+56 9 9999 0000" value={datos.whatsapp_central} error={errores.whatsapp_central} onChange={(e) => cambiar('whatsapp_central', e.target.value)} />
        </div>
      </fieldset>
      <fieldset className={estilos.tarjeta}>
        <legend>Reserva pública</legend>
        <div className={c.grilla}>
          {NUMEROS.map(({ campo, etiqueta, min, max, ayuda }) => (
            <Campo
              key={campo}
              etiqueta={etiqueta}
              type="number"
              inputMode="numeric"
              min={min}
              max={max}
              ayuda={`${ayuda} Entre ${min} y ${max}.`}
              value={datos[campo]}
              error={errores[campo]}
              onChange={(e) => cambiar(campo, e.target.value)}
            />
          ))}
        </div>
      </fieldset>
      {guardado && <Aviso>Cambios guardados.</Aviso>}
      <div>
        <Boton type="submit" cargando={guardar.isPending}>
          Guardar cambios
        </Boton>
      </div>
    </form>
  );
}
