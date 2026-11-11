# Diseño del panel y de la app del conductor

Usan los mismos tokens, la misma tipografía y las mismas medidas que `portal/README.md`. Las imágenes tienen datos ficticios.
- `panel/`: 1440 px. Panel del SaaS para administrador y despachador.
- `conductor/`: 390 px. App del conductor (Capacitor).

## Panel
- Barra lateral de 248 px con secciones Operación, Flota y Gestión. El ítem activo lleva fondo --color-tiffany-50, texto --color-primario-700 y una marca a la izquierda. El despachador solo ve Operación.
- Barra superior de 76 px: título, subtítulo o ruta, acciones y notificaciones.
- Tablas: encabezado en mayúsculas de 12 px, peso 700, color --texto-suave, sobre fondo #F8FCFC. Filas de 50 a 56 px. Números alineados a la derecha. Acciones en el menú ⋯.
- En el panel, inputs y botones miden 42 px de alto (densidad de escritorio).
- Un solo mapa estado → insignia para todo el sistema:
  - Por confirmar: neutra.
  - Sin asignar: revisión.
  - Asignada: info.
  - En curso: ok.
  - Finalizada: neutra.
  - Cancelada: peligro.
  - Conductor: en fila (info), en camino y en viaje (ok), no disponible (neutra).
  - Convenio: en revisión, aprobado, rechazado, inactivo.
  - Vuelo: a tiempo (ok), atrasado (revisión), aterrizó (info).
- Colores de los marcadores del mapa: en fila = primario-700, en camino = éxito, en viaje = primario-900, no disponible = #9AA9AB.

## Apariencia por empresa (pantalla 15, ejemplo aplicado en la 16)
Cada empresa define:
- logo (PNG o SVG; si no hay logo, se usan las iniciales);
- nombre visible e iniciales;
- color principal y color de acento, elegidos de 6 combinaciones o con un color libre.

Con esos datos se calculan los tokens:
- primario-700 = el color principal;
- primario-900 = el principal oscurecido;
- acento = tiffany;
- acento-50, fondo, suave y borde = mezclas del acento o del principal con blanco;
- degradés de botón, hero y destacado a partir de esos valores.

Reglas:
- El texto blanco sobre primario-700 debe cumplir AA (4,5 : 1). Si no cumple, el color se oscurece automáticamente y la pantalla lo avisa.
- Los colores de estado (peligro, éxito, revisión) NO cambian con la marca.
- La apariencia se aplica como variables CSS en tiempo de ejecución, en el portal (por slug, sin sesión), en el panel, en la app del conductor y en los correos. Con casillas se elige dónde aplicarla.
- Valor por defecto: Tiffany degradé.

## App del conductor
- Texto base de 16 px. Botones de 56 px. La acción principal va a todo el ancho, abajo.
- Barra inferior: Inicio, Mi turno, Cuenta.
- Lo más visible: el estado y la posición en la fila del aeropuerto. Durante un viaje, una barra de 4 pasos: En camino, En zona, A bordo, Finalizado.
- Viaje asignado: pantalla completa en degradé hero, con anillo de cuenta regresiva de 60 s y botones Rechazar y Aceptar.
- Al finalizar: monto cobrado y método de pago (efectivo, transferencia o convenio).
- No se cambian los permisos, el GPS ni nada nativo.
