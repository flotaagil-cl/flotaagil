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
          // HU-34: queda aprobado y sin cuenta; las empresas con cuenta se registran en el portal.
          const { id } = await crear.mutateAsync(datos);
          navegar(`/convenios/${id}`, { replace: true });
        }}
      />
    </section>
  );
}
