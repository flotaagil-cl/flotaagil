import { useConversacionesChat } from './api';

/** HU-63: no leídos del chat junto a «Chat» en el menú del panel. */
export function NoLeidosChat({ className }: { className?: string }) {
  const consulta = useConversacionesChat();
  const total = (consulta.data ?? []).reduce((suma, c) => suma + c.no_leidos, 0);
  if (!total) return null;
  return <span className={className}>{` ${total} sin leer`}</span>;
}
