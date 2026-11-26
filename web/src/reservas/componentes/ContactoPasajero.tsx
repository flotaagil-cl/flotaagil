import estilos from '../../componentes/panel.module.css';

/** «+56912345678» → «56912345678» para wa.me (solo dígitos, con el código de país). */
function soloDigitos(telefono: string): string {
  return telefono.replace(/\D/g, '');
}

/**
 * HU-55 (CC-22): junto al teléfono del pasajero, «Llamar» (tel:) y «Abrir en WhatsApp» (wa.me). Abren el teléfono o
 * el WhatsApp del propio despachador: FlotaÁgil no envía nada ni usa ninguna API. Sin teléfono (cuenta eliminada,
 * DC-50) no hay botones.
 */
export function ContactoPasajero({
  telefono,
  compacto = false,
  nombre,
}: {
  telefono: string | null | undefined;
  compacto?: boolean;
  nombre?: string;
}) {
  if (!telefono) return <span className={compacto ? estilos.secundario : undefined}>Sin teléfono</span>;
  const sufijo = nombre ? ` a ${nombre}` : '';
  const claseEnlace = compacto ? estilos.enlaceContactoCompacto : estilos.enlaceContacto;
  const enlaces = (
    <>
      <a href={`tel:${telefono}`} className={claseEnlace} aria-label={compacto ? `Llamar${sufijo}` : undefined}>
        Llamar
      </a>
      <a
        href={`https://wa.me/${soloDigitos(telefono)}`}
        target="_blank"
        rel="noopener noreferrer"
        className={claseEnlace}
        aria-label={compacto ? `WhatsApp${sufijo}` : undefined}
      >
        {compacto ? 'WhatsApp' : 'Abrir en WhatsApp'}
      </a>
    </>
  );

  if (compacto) {
    return (
      <div className={estilos.contactoCompacto}>
        <span className={estilos.telefonoCompacto}>{telefono}</span>
        <div className={estilos.accionesContacto}>{enlaces}</div>
      </div>
    );
  }

  return (
    <span className={estilos.contacto}>
      <span>{telefono}</span>
      {enlaces}
    </span>
  );
}
