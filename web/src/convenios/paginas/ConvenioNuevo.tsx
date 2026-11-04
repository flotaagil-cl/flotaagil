import { useNavigate } from 'react-router';
import { useCrearConvenio } from '../api';
import { FormularioConvenio } from '../componentes';

export function ConvenioNuevo() {
  const crear = useCrearConvenio();
  const navegar = useNavigate();
  return (
    <section>
      <h1>Nuevo convenio</h1>
      <FormularioConvenio
        iniciales={{ cliente_nombre: '', cliente_rut: '' }}
        textoEnviar="Crear convenio"
        volverA="/convenios"
        enviar={async (datos) => {
          const { id, password } = await crear.mutateAsync(datos);
          // La contraseña viaja en el estado de la navegación: no queda en la URL ni en el almacenamiento.
          navegar(`/convenios/${id}`, { replace: true, state: { password } });
        }}
      />
    </section>
  );
}
