/** CC-21 (DC-86): el nombre con que la empresa se muestra en los encabezados. */
export function nombreVisible(apariencia: { nombre_marca?: string } | null | undefined, razonSocial: string): string {
  return apariencia?.nombre_marca || razonSocial;
}
