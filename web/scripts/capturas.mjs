// Capturas de evidencia a 390 y 1440 px (CLAUDE.md, «Informes y evidencias»).
//
// Uso:  npm run capturas -- HU-31 HU-36     (sin argumentos: todas las HU de PANTALLAS)
//
// Necesita el web en CAPTURAS_URL (por defecto http://localhost:5173), el backend con `datos_demo`
// y la clave de los usuarios demo en DATOS_DEMO_PASSWORD. Las pantallas del pasajero entran con
// CAPTURAS_PASAJERO_EMAIL y CAPTURAS_PASAJERO_PASSWORD: una cuenta sintética con clave temporal, que se
// invalida al terminar. Las claves no se imprimen ni se guardan.
// Usa el Edge instalado (CAPTURAS_CANAL=chrome para Chrome): no descarga navegadores.
// Guarda docs/evidencias/HU-xx/<nombre>-390.png y <nombre>-1440.png. Solo datos sintéticos: no capturar
// pantallas que muestren una contraseña temporal sin invalidarla después.
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const EVIDENCIAS = join(RAIZ, 'docs', 'evidencias');
const URL_BASE = process.env.CAPTURAS_URL ?? 'http://localhost:5173';
const EMPRESA = 'transportes-andes';
const PORTAL = `/solicitar/${EMPRESA}`;
// HU-63: alerta de llegada de un viaje sintético con conductor (se envía al cerrar la transacción).
const LLEGADA = [
  'from django.db import transaction',
  'from apps.chat.servicios import alertar_llegada',
  'from apps.reservas.models import Viaje',
  `v = Viaje.objects.filter(empresa__slug="${EMPRESA}", conductor__isnull=False).order_by("pk").first()`,
  'with transaction.atomic(): alertar_llegada(v)',
].join('\n');
// HU-63: el despacho escribe en el hilo central de conductor1.
const MENSAJE_CENTRAL = [
  'from apps.chat.models import Conversacion',
  'from apps.chat.servicios import publicar',
  'from apps.cuentas.models import Usuario',
  `d = Usuario.objects.get(email="despacho@${EMPRESA}.example")`,
  `c = Conversacion.objects.get(tipo="CENTRAL", conductor__usuario__email="conductor1@${EMPRESA}.example")`,
  'publicar(d, c, "Tu próximo pasajero espera en la puerta 3.")',
].join('\n');

const ANCHOS = [
  { sufijo: '390', opciones: { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true } },
  { sufijo: '1440', opciones: { viewport: { width: 1440, height: 900 } } },
];

/**
 * Pantallas por HU. `sesion`: alias del usuario demo (admin, despacho, convenio), 'pasajero' o null sin sesión.
 * `destino`: ruta a la que debe llegar (por defecto, la misma `ruta`); si termina en otra, la captura falla.
 * `accion`: lo que se hace en la página antes de capturar (abrir un diálogo, por ejemplo).
 */
const PANTALLAS = {
  'HU-31': [{ nombre: 'panel-caja', ruta: '/caja', sesion: 'admin' }],
  'HU-32': [{ nombre: 'panel-reserva-contingencia', ruta: '/reservas/contingencia', sesion: 'despacho' }],
  'HU-33': [
    { nombre: 'ingresar-panel', ruta: '/login', sesion: null },
    { nombre: 'portal-ingresar', ruta: `${PORTAL}/ingresar`, sesion: null },
  ],
  'HU-34': [
    { nombre: 'portal-registro-empresa', ruta: `${PORTAL}/registro-empresa`, sesion: null },
    { nombre: 'panel-convenios', ruta: '/convenios', sesion: 'admin' },
    { nombre: 'mi-convenio', ruta: '/mi-convenio', sesion: 'convenio' },
  ],
  'HU-35': [{ nombre: 'portal-crear-cuenta', ruta: `${PORTAL}/cuenta`, sesion: null }],
  'HU-36': [{ nombre: 'panel-usuarios', ruta: '/usuarios', sesion: 'admin' }],
  // La raíz del portal lleva a «Ingresar» desde CC-18; el marco y los tokens se ven en la página de privacidad.
  'HU-37': [{ nombre: 'portal-marco-privacidad', ruta: `${PORTAL}/privacidad`, sesion: null }],
  'HU-40': [{ nombre: 'pedir-sin-sesion', ruta: '/pedir', sesion: null, destino: /\/(login|solicitar\/[^/]+\/ingresar)/ }],
  // HU-50 (CC-22): taxi-pacifico no tiene el módulo de cuentas; transportes-andes sí.
  'HU-50': [
    { nombre: 'portal-sin-modulo-cuenta', ruta: '/solicitar/taxi-pacifico/cuenta', sesion: null },
    { nombre: 'panel-inicio-sin-modulo', ruta: '/', sesion: 'admin@taxi-pacifico.example' },
  ],
  // HU-51 (CC-22): reserva pública. Los enlaces de confirmación (uno por ancho) vienen en CAPTURAS_TOKEN_390 y
  // CAPTURAS_TOKEN_1440: son de reservas sintéticas creadas para la captura.
  'HU-51': [
    { nombre: 'reserva-publica', ruta: '/solicitar/taxi-pacifico', sesion: null },
    {
      nombre: 'reserva-tus-datos',
      ruta: '/solicitar/taxi-pacifico',
      sesion: null,
      accion: async (pagina) => {
        await pagina.getByLabel('Origen').fill('Av. Providencia 1208, Providencia');
        await pagina.getByLabel('Destino').fill('Plaza de Armas, Santiago');
        await pagina.getByRole('button', { name: 'Pedir mi traslado' }).click();
        await pagina.getByRole('heading', { name: 'Tus datos' }).waitFor();
      },
    },
    {
      nombre: 'reserva-confirmada',
      ruta: (sufijo) => `/solicitar/taxi-pacifico/confirmar/${process.env[`CAPTURAS_TOKEN_${sufijo}`] ?? 'falta-token'}`,
      sesion: null,
      destino: /\/confirmar\//,
      accion: async (pagina) => {
        await pagina.getByRole('heading', { name: 'Reserva confirmada' }).waitFor();
      },
    },
  ],
  // HU-52 (CC-22): reservas «Sin confirmar» en el panel de taxi-pacifico. CAPTURAS_VIAJE: una pendiente vencida.
  'HU-52': [
    {
      nombre: 'panel-sin-confirmar-listado',
      ruta: '/reservas?sin_confirmar=true&desde=',
      sesion: 'admin@taxi-pacifico.example',
      destino: /^\/reservas$/,
    },
    {
      nombre: 'panel-sin-confirmar-detalle',
      ruta: () => `/reservas/${process.env.CAPTURAS_VIAJE ?? '0'}`,
      sesion: 'admin@taxi-pacifico.example',
      destino: /^\/reservas\/\d+$/,
    },
  ],
  // HU-53 (CC-22): solicitud pública de convenio y su revisión por el despachador. CAPTURAS_CONVENIO: una en revisión.
  'HU-53': [
    { nombre: 'portal-solicitud-convenio', ruta: '/solicitar/taxi-pacifico/convenio', sesion: null },
    {
      nombre: 'panel-aprobar-convenio',
      ruta: () => `/convenios/${process.env.CAPTURAS_CONVENIO ?? '0'}`,
      sesion: 'despacho@taxi-pacifico.example',
      destino: /^\/convenios\/\d+$/,
      accion: async (pagina) => {
        await pagina.getByRole('button', { name: 'Aprobar' }).click();
        await pagina.getByLabel(/Correos autorizados/).waitFor();
      },
    },
  ],
  // HU-54 (CC-22): reserva con el RUT de un convenio aprobado (Constructora Sintetica, 76123456-0) desde un correo no
  // autorizado, y la página donde el contacto del convenio decide.
  'HU-54': [
    {
      nombre: 'reserva-espera-autorizacion',
      ruta: '/solicitar/taxi-pacifico',
      sesion: null,
      accion: async (pagina) => {
        await pagina.getByLabel('Origen').fill('Av. Vitacura 2939, Las Condes');
        await pagina.getByLabel('Destino').fill('Plaza de Armas, Santiago');
        await pagina.getByRole('button', { name: 'Pedir mi traslado' }).click();
        await pagina.getByLabel('Nombre y apellido').fill('Pablo Sintético');
        await pagina.getByLabel('Correo', { exact: true }).fill(`pablo.${Date.now()}@correo.example`);
        await pagina.getByLabel('Teléfono de contacto').fill('+56900009801');
        await pagina.getByRole('checkbox', { name: '¿Es una empresa?' }).check();
        await pagina.getByLabel('Razón social').fill('Constructora Sintetica Ltda.');
        await pagina.getByLabel('RUT de la empresa').fill('76123456-0');
        await pagina.getByLabel('Persona de contacto').fill('Carla Contacto');
        await pagina.getByRole('checkbox', { name: /aviso de privacidad/ }).check();
        await pagina.getByRole('button', { name: 'Enviar solicitud' }).click();
        await pagina.getByRole('heading', { name: /espera la autorización/ }).waitFor();
      },
    },
    { nombre: 'autorizar-reserva', ruta: '/solicitar/taxi-pacifico/autorizar/enlace-de-ejemplo', sesion: null, destino: /\/autorizar\// },
  ],
  // HU-55 (CC-22): Llamar y Abrir en WhatsApp en el detalle de una reserva. CAPTURAS_VIAJE: una con teléfono.
  'HU-55': [
    {
      nombre: 'panel-contacto-pasajero',
      ruta: () => `/reservas/${process.env.CAPTURAS_VIAJE ?? '0'}`,
      sesion: 'despacho',
      destino: /^\/reservas\/\d+$/,
    },
  ],
  // HU-56 (CC-22): encuesta del correo (antes de responder) y el color del vehículo para el aviso de conductor.
  'HU-56': [
    { nombre: 'encuesta-correo', ruta: '/solicitar/taxi-pacifico/encuesta/enlace-de-ejemplo', sesion: null, destino: /\/encuesta\// },
    { nombre: 'panel-vehiculo-color', ruta: '/vehiculos/nuevo', sesion: 'admin@taxi-pacifico.example' },
  ],
  // HU-57 (CC-20): el panel con el sistema visual del portal. Se corre con CAPTURAS_PREFIJO=antes- sobre main.
  'HU-57': [
    { nombre: 'panel-inicio', ruta: '/', sesion: 'admin' },
    { nombre: 'panel-reservas', ruta: '/reservas', sesion: 'admin' },
    { nombre: 'panel-reserva', ruta: '/reservas/5', sesion: 'admin' },
    { nombre: 'panel-nueva-reserva', ruta: '/reservas/nueva', sesion: 'despacho' },
    { nombre: 'panel-mapa', ruta: '/mapa', sesion: 'despacho' },
    { nombre: 'panel-vehiculos', ruta: '/vehiculos', sesion: 'admin' },
    { nombre: 'panel-conductores', ruta: '/conductores', sesion: 'admin' },
    { nombre: 'panel-conversaciones', ruta: '/conversaciones', sesion: 'despacho' },
    { nombre: 'panel-reportes', ruta: '/reportes', sesion: 'admin' },
    { nombre: 'panel-usuarios', ruta: '/usuarios', sesion: 'admin' },
    { nombre: 'panel-caja', ruta: '/caja', sesion: 'admin' },
    { nombre: 'panel-convenios', ruta: '/convenios', sesion: 'admin' },
  ],
  // HU-58 (CC-20): portal restante con el sistema visual (antes con CAPTURAS_PREFIJO=antes-).
  'HU-58': [
    { nombre: 'portal-registro-empresa', ruta: '/solicitar/transportes-andes/registro-empresa', sesion: null },
    { nombre: 'portal-privacidad', ruta: '/solicitar/transportes-andes/privacidad', sesion: null },
    { nombre: 'mi-convenio', ruta: '/mi-convenio', sesion: 'convenio' },
  ],
  // HU-59 (CC-20): la app del conductor. Se corre con CAPTURAS_URL apuntando al servidor de la app (npx vite en app/).
  'HU-59': [
    { nombre: 'app-ingresar', ruta: '/', sesion: null },
    {
      nombre: 'app-inicio',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await pagina.getByLabel('Correo').fill('conductor1@transportes-andes.example');
        await pagina.getByLabel('Contraseña').fill(process.env.DATOS_DEMO_PASSWORD ?? '');
        await pagina.getByRole('button', { name: 'Ingresar' }).click();
        await pagina.getByRole('heading', { name: /Hola|ubicación|Consentimiento|contraseña/i }).first().waitFor();
      },
    },
    // Con datos preparados para conductor1 (asignación pendiente o viaje en curso), ver la nota de HU-59.
    {
      nombre: 'app-viaje-asignado',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await ingresarApp(pagina);
        await pagina.getByRole('heading', { name: 'Nuevo viaje asignado' }).waitFor();
      },
    },
    {
      nombre: 'app-viaje-en-curso',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await ingresarApp(pagina);
        await pagina.getByText(/Navegar/).first().waitFor();
      },
    },
    {
      nombre: 'app-mi-turno',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await ingresarApp(pagina);
        await pagina.getByRole('button', { name: 'Mi turno' }).click();
        await pagina.getByRole('heading', { name: 'Mi turno' }).waitFor();
      },
    },
  ],
  // HU-61 y HU-62 (CC-19): chat de trabajo con los mensajes sintéticos de datos_demo. Las de la app se corren con
  // CAPTURAS_URL en el servidor de la app y CAPTURAS_SOLO=app-chat,app-chat-central.
  'HU-61': [
    { nombre: 'panel-chat', ruta: '/chat', sesion: 'despacho' },
    {
      nombre: 'panel-chat-central',
      ruta: '/chat',
      sesion: 'despacho',
      destino: /^\/chat\/\d+$/,
      accion: async (pagina) => {
        await pagina.getByRole('link', { name: /Conductor · .*Llegué/ }).first().click();
        await pagina.getByRole('list', { name: 'Mensajes' }).waitFor();
      },
    },
    {
      nombre: 'app-chat',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await ingresarApp(pagina);
        await pagina.getByRole('button', { name: /^Chat/ }).click();
        await pagina.getByRole('heading', { name: 'Chat' }).waitFor();
      },
    },
    {
      nombre: 'app-chat-central',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await ingresarApp(pagina);
        await pagina.getByRole('button', { name: /^Chat/ }).click();
        await pagina.getByRole('button', { name: /^Central/ }).click();
        await pagina.getByRole('group', { name: 'Respuestas rápidas' }).waitFor();
      },
    },
  ],
  'HU-62': [
    {
      nombre: 'panel-chat-grupo',
      ruta: '/chat',
      sesion: 'despacho',
      destino: /^\/chat\/\d+$/,
      accion: async (pagina) => {
        await pagina.getByRole('link', { name: /Turno noche/ }).click();
        await pagina.getByRole('button', { name: 'Gestionar grupo' }).click();
        await pagina.getByRole('dialog', { name: 'Gestionar grupo' }).getByRole('list').waitFor();
      },
    },
    {
      nombre: 'panel-chat-nuevo-grupo',
      ruta: '/chat',
      sesion: 'despacho',
      accion: async (pagina) => {
        await pagina.getByRole('button', { name: 'Nuevo grupo' }).click();
        await pagina.getByRole('dialog', { name: 'Nuevo grupo' }).getByRole('checkbox').first().waitFor();
      },
    },
    { nombre: 'panel-chat-moderacion', ruta: '/chat/moderacion', sesion: 'admin' },
  ],
  // HU-63 (CC-19): la llegada se dispara en el backend (docker compose) mientras el panel escucha /ws/chat/.
  'HU-63': [
    {
      nombre: 'panel-alerta-llegada',
      ruta: '/',
      sesion: 'despacho',
      accion: async (pagina) => {
        await pagina.waitForTimeout(1500);
        execFileSync('docker', ['compose', '-f', '../infra/docker-compose.dev.yml', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c', LLEGADA]);
        await pagina.getByRole('status', { name: 'Llegadas al origen' }).waitFor();
      },
    },
    { nombre: 'panel-chat-no-leidos', ruta: '/chat', sesion: 'admin' },
    // En la app (CAPTURAS_URL del servidor de la app): el despacho escribe a conductor1 mientras está en el inicio.
    {
      nombre: 'app-aviso-chat',
      ruta: '/',
      sesion: null,
      accion: async (pagina) => {
        await ingresarApp(pagina);
        await pagina.getByRole('button', { name: /^Chat/ }).waitFor();
        await pagina.waitForTimeout(1500);
        execFileSync('docker', ['compose', '-f', '../infra/docker-compose.dev.yml', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c', MENSAJE_CENTRAL]);
        await pagina.getByText(/Nuevo mensaje de Central/).waitFor();
      },
    },
  ],
  // HU-64 (CC-19): activación por correo. Las cuentas sintéticas se crean en el backend (clave de los usuarios demo).
  'HU-64': [
    { nombre: 'portal-crear-cuenta', ruta: `${PORTAL}/cuenta`, sesion: null },
    {
      nombre: 'portal-activa-tu-cuenta',
      ruta: `${PORTAL}/activar`,
      sesion: null,
      accion: async (pagina) => {
        tokenHU64();
        await pagina.getByLabel('Correo').fill('pendiente-hu64@correo.example');
        await pagina.getByLabel('Contraseña').fill(process.env.DATOS_DEMO_PASSWORD ?? '');
        await pagina.getByRole('button', { name: 'Continuar' }).click();
        await pagina.getByRole('list', { name: 'Activación de tu cuenta' }).waitFor();
      },
    },
    {
      nombre: 'portal-cuenta-activada',
      ruta: () => `${PORTAL}/activar/${tokenHU64()}`,
      sesion: null,
      destino: /\/activar\//,
      accion: async (pagina) => {
        await pagina.getByRole('heading', { name: '¡Tu cuenta está activa!' }).waitFor();
      },
    },
    { nombre: 'portal-enlace-invalido', ruta: `${PORTAL}/activar/enlace-de-ejemplo`, sesion: null, destino: /\/activar\// },
    { nombre: 'mi-perfil-telefono', ruta: '/mi-perfil', sesion: 'activa-hu64@correo.example' },
  ],
  // HU-65 (CC-19): «Tu viaje» con los avisos (Web Push o correo) y la casilla de «Mi perfil», con la cuenta de HU-64.
  'HU-65': [
    { nombre: 'tu-viaje-avisos', ruta: () => `/mis-viajes/${viajeHU65()}`, sesion: 'activa-hu64@correo.example' },
    { nombre: 'mi-perfil-avisos', ruta: '/mi-perfil', sesion: 'activa-hu64@correo.example' },
    { nombre: 'portal-crear-cuenta-avisos', ruta: `${PORTAL}/cuenta`, sesion: null },
  ],
  // HU-66 (CC-19): chat con el conductor, soporte y lectura auditada de la central (viaje de la cuenta de HU-64).
  'HU-66': [
    { nombre: 'tu-viaje-chat', ruta: () => `/mis-viajes/${viajeHU66()}`, sesion: 'activa-hu64@correo.example' },
    { nombre: 'portal-soporte', ruta: '/soporte', sesion: 'activa-hu64@correo.example' },
    {
      nombre: 'panel-lectura-chat',
      ruta: () => `/reservas/${viajeHU66()}`,
      sesion: 'despacho',
      accion: async (pagina) => {
        await pagina.getByRole('button', { name: 'Ver chat con el pasajero' }).click();
        await pagina.getByRole('dialog', { name: 'Chat del viaje (solo lectura)' }).getByRole('list').waitFor();
      },
    },
  ],
  'HU-45': [
    { nombre: 'mi-perfil', ruta: '/mi-perfil', sesion: 'pasajero' },
    {
      nombre: 'eliminar-cuenta',
      ruta: '/mi-perfil',
      sesion: 'pasajero',
      accion: async (pagina) => {
        await pagina.getByRole('button', { name: /Eliminar mi cuenta/ }).click();
        await pagina.getByRole('dialog', { name: '¿Eliminar tu cuenta?' }).waitFor();
      },
    },
  ],
};

// HU-64: una cuenta pendiente y otra para activar (sintéticas, con la clave de los usuarios demo del contenedor).
const CUENTAS_HU64 = [
  'import os',
  'from apps.cuentas.models import Empresa',
  'from apps.reservas import cuentas_pasajero as c',
  'from apps.reservas.models import CuentaPasajero',
  `e = Empresa.objects.get(slug="${EMPRESA}")`,
  'def asegurar(email, tel):',
  '    cuenta = CuentaPasajero.objects.filter(usuario__email=email).first()',
  '    datos = {"nombre": "Paula Sintética", "telefono": tel, "email": email, "password": os.environ["DATOS_DEMO_PASSWORD"]}',
  '    return cuenta or c.registrar(e, datos)',
  'asegurar("pendiente-hu64@correo.example", "+56900006401")',
  'print(c.token_activacion(asegurar("activa-hu64@correo.example", "+56900006402")))',
].join('\n');
let tokenActivacion = null;

/** HU-64: crea (si faltan) las cuentas sintéticas y devuelve el token de activación de la segunda. */
function tokenHU64() {
  tokenActivacion ??= execFileSync('docker', ['compose', '-f', '../infra/docker-compose.dev.yml', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c', CUENTAS_HU64], {
    encoding: 'utf8',
  })
    .trim()
    .split('\n')
    .at(-1);
  return tokenActivacion;
}

// HU-65: un viaje pedido por la cuenta activa de HU-64 (con la API, como lo haría el portal).
const VIAJE_HU65 = [
  'from datetime import timedelta',
  'from django.utils import timezone',
  'from rest_framework.test import APIClient',
  'from apps.reservas.models import CuentaPasajero',
  'from apps.reservas.cuentas_pasajero import reservas_de',
  'cuenta = CuentaPasajero.objects.get(usuario__email="activa-hu64@correo.example")',
  'viaje = reservas_de(cuenta).filter(estado="SOLICITADO").first()',
  'if viaje is None:',
  '    c = APIClient(HTTP_HOST="localhost")',
  '    c.force_authenticate(cuenta.usuario)',
  '    datos = {"origen_dir": "Av. Providencia 1234, Providencia", "destino_dir": "Plaza de Armas, Santiago",',
  '             "recogida_en": (timezone.now() + timedelta(hours=3)).isoformat(), "acepta_privacidad": True}',
  '    viaje_id = c.post("/api/mi-cuenta/solicitudes/", datos, format="json").data["id"]',
  'else:',
  '    viaje_id = viaje.pk',
  'print(viaje_id)',
].join('\n');
let viajeActivo = null;

function viajeHU65() {
  tokenHU64();
  viajeActivo ??= execFileSync('docker', ['compose', '-f', '../infra/docker-compose.dev.yml', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c', VIAJE_HU65], {
    encoding: 'utf8',
  })
    .trim()
    .split('\n')
    .at(-1);
  return viajeActivo;
}

// HU-66: el viaje de la cuenta de HU-64 pasa a ACEPTADO con conductor4, con mensajes sintéticos en su chat y soporte.
const PREPARAR_HU66 = [
  'from apps.chat import servicios as s',
  'from apps.flota.models import Conductor',
  'from apps.reservas.cuentas_pasajero import reservas_de',
  'from apps.reservas.models import CuentaPasajero, Viaje',
  'cuenta = CuentaPasajero.objects.get(usuario__email="activa-hu64@correo.example")',
  'v = reservas_de(cuenta).order_by("-pk").first()',
  `c = Conductor.objects.get(usuario__email="conductor4@${EMPRESA}.example")`,
  'from apps.flota.models import ConductorVehiculo',
  'veh = ConductorVehiculo.objects.filter(conductor=c).first().vehiculo',
  'Viaje.objects.filter(pk=v.pk).update(conductor=c, vehiculo=veh, estado="ACEPTADO")',
  'v.refresh_from_db()',
  'chat = s.conversacion_de_viaje(v)',
  'if not chat.mensajes.exists():',
  '    s.publicar(c.usuario, chat, "Hola, voy en camino. Llego en 10 minutos.")',
  '    s.publicar(cuenta.usuario, chat, "Perfecto, te espero en la entrada principal.")',
  'soporte = s.soporte_de(cuenta.usuario)',
  'if not soporte.mensajes.exists():',
  '    s.publicar(cuenta.usuario, soporte, f"[Viaje N.º {v.pk}] ¿Puedo llevar una bicicleta plegable?")',
  'print(v.pk)',
].join('\n');
let viajeConChat = null;

function viajeHU66() {
  viajeHU65();
  viajeConChat ??= execFileSync('docker', ['compose', '-f', '../infra/docker-compose.dev.yml', 'exec', '-T', 'backend', 'python', 'manage.py', 'shell', '-c', PREPARAR_HU66], {
    encoding: 'utf8',
  })
    .trim()
    .split('\n')
    .at(-1);
  return viajeConChat;
}

/** HU-59: ingreso a la app del conductor con conductor1 (clave de los usuarios demo). */
async function ingresarApp(pagina) {
  // Las pantallas sin sesión comparten el contexto del ancho: si la app ya quedó con la sesión, no hay login.
  if (!(await pagina.getByLabel('Correo').isVisible({ timeout: 3000 }).catch(() => false))) return;
  await pagina.getByLabel('Correo').fill('conductor1@transportes-andes.example');
  await pagina.getByLabel('Contraseña').fill(process.env.DATOS_DEMO_PASSWORD ?? '');
  await pagina.getByRole('button', { name: 'Ingresar' }).click();
}

/** Correo y clave de cada sesión: los usuarios demo comparten DATOS_DEMO_PASSWORD; el pasajero tiene la suya. */
function credenciales(alias) {
  if (alias === 'pasajero') {
    const email = process.env.CAPTURAS_PASAJERO_EMAIL;
    const clave = process.env.CAPTURAS_PASAJERO_PASSWORD;
    if (!email || !clave) throw new Error('Faltan CAPTURAS_PASAJERO_EMAIL y CAPTURAS_PASAJERO_PASSWORD.');
    return { email, clave };
  }
  const clave = process.env.DATOS_DEMO_PASSWORD;
  if (!clave) throw new Error('Falta DATOS_DEMO_PASSWORD para las pantallas con sesión.');
  // Un alias con @ es el correo completo (por ejemplo, un usuario de la empresa sin el módulo de cuentas).
  return { email: alias.includes('@') ? alias : `${alias}@${EMPRESA}.example`, clave };
}

async function iniciarSesion(pagina, alias) {
  const { email, clave } = credenciales(alias);
  await pagina.goto(`${URL_BASE}/login`);
  await pagina.getByLabel('Correo').fill(email);
  await pagina.getByLabel('Contraseña').fill(clave);
  await pagina.getByRole('button', { name: 'Ingresar' }).click();
  try {
    await pagina.waitForURL((url) => url.pathname !== '/login', { timeout: 15000 });
  } catch {
    const aviso = (await pagina.getByRole('alert').first().textContent().catch(() => '')) || 'sin aviso';
    throw new Error(`No se pudo iniciar sesión como ${email}: ${aviso.trim()}`);
  }
  if (new URL(pagina.url()).pathname === '/primer-ingreso') {
    throw new Error(`${email} pide primer ingreso: corre datos_demo de nuevo.`);
  }
}

function llegoA(pagina, pantalla) {
  const ruta = new URL(pagina.url()).pathname;
  return pantalla.destino ? pantalla.destino.test(ruta) : ruta === pantalla.rutaFinal;
}

async function main() {
  const pedidas = process.argv.slice(2);
  const hus = pedidas.length ? pedidas : Object.keys(PANTALLAS);
  const desconocidas = hus.filter((hu) => !PANTALLAS[hu]);
  if (desconocidas.length) throw new Error(`Sin pantallas definidas: ${desconocidas.join(', ')}`);

  const navegador = await chromium.launch({ channel: process.env.CAPTURAS_CANAL ?? 'msedge', headless: true });
  let fallas = 0;
  try {
    for (const { sufijo, opciones } of ANCHOS) {
      // Un contexto por usuario y ancho: la sesión se reutiliza entre pantallas.
      const contextos = new Map();
      const contextoDe = async (alias) => {
        const clave = alias ?? '(sin sesión)';
        if (!contextos.has(clave)) {
          const ctx = await navegador.newContext({ locale: 'es-CL', timezoneId: 'America/Santiago', ...opciones });
          if (alias) await iniciarSesion(await ctx.newPage(), alias);
          contextos.set(clave, ctx);
        }
        return contextos.get(clave);
      };
      for (const hu of hus) {
        mkdirSync(join(EVIDENCIAS, hu), { recursive: true });
        // CAPTURAS_SOLO=nombre1,nombre2 toma solo esas pantallas (cuando cada una necesita datos distintos).
        const solo = process.env.CAPTURAS_SOLO?.split(',');
        for (const pantalla of PANTALLAS[hu].filter((p) => !solo || solo.includes(p.nombre))) {
          const ctx = await contextoDe(pantalla.sesion);
          const pagina = await ctx.newPage();
          // La ruta puede depender del ancho (p. ej. un enlace de un solo uso por captura).
          pantalla.rutaFinal = typeof pantalla.ruta === 'function' ? pantalla.ruta(sufijo) : pantalla.ruta;
          await pagina.goto(`${URL_BASE}${pantalla.rutaFinal}`);
          await pagina.waitForLoadState('networkidle');
          if (pantalla.accion) await pantalla.accion(pagina);
          const titulo = (await pagina.locator('h1').first().textContent({ timeout: 10000 }).catch(() => '')) ?? '';
          // CAPTURAS_PREFIJO (p. ej. «antes-») separa las capturas del antes y el después (CC-20).
          const archivo = join(EVIDENCIAS, hu, `${process.env.CAPTURAS_PREFIJO ?? ''}${pantalla.nombre}-${sufijo}.png`);
          if (llegoA(pagina, pantalla)) {
            await pagina.screenshot({ path: archivo, fullPage: true });
            console.log(`ok   ${hu} ${pantalla.nombre}-${sufijo} · ${new URL(pagina.url()).pathname} · «${titulo.trim()}»`);
          } else {
            fallas += 1;
            console.log(`FALLA ${hu} ${pantalla.nombre}-${sufijo}: terminó en ${new URL(pagina.url()).pathname}`);
          }
          await pagina.close();
        }
      }
      for (const ctx of contextos.values()) await ctx.close();
    }
  } finally {
    await navegador.close();
  }
  if (fallas) {
    console.error(`${fallas} captura(s) no llegaron a su pantalla.`);
    process.exit(1);
  }
}

await main();
