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
  return (
    <span className={estilos.contacto}>
      <span>{telefono}</span>
      <a href={`tel:${telefono}`} className={estilos.enlaceContacto} aria-label={compacto ? `Llamar${sufijo}` : undefined}>
        Llamar
      </a>
      <a
        href={`https://wa.me/${soloDigitos(telefono)}`}
        target="_blank"
        rel="noopener noreferrer"
        className={estilos.enlaceContacto}
        aria-label={compacto ? `WhatsApp${sufijo}` : undefined}
      >
        {compacto ? 'WhatsApp' : 'Abrir en WhatsApp'}
      </a>
    </span>
  );
}
