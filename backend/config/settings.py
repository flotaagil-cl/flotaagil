"""Configuración de FlotaÁgil. Los valores sensibles o propios del entorno se leen de variables de entorno."""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
if (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")

INSTALLED_APPS = [
    # Daphne primero: `runserver` sirve HTTP y WebSocket (ASGI) en desarrollo.
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "channels",
    "django_filters",
    "apps.cuentas",
    "apps.flota",
    "apps.convenios",
    "apps.reservas",
    "apps.aeropuerto",
    "apps.auditoria",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Capa de canales (HU-02): grupos por empresa para el mapa en tiempo real.
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [env("REDIS_URL", default="redis://localhost:6379/0")]},
    }
}
# HU-02: una posición más antigua que esto se marca como no confiable en el mapa.
POSICION_CONFIABLE_SEGUNDOS = env.int("POSICION_CONFIABLE_SEGUNDOS", default=60)

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# PostgreSQL 16 + PostGIS: DATABASE_URL con esquema postgis://
DATABASES = {"default": env.db("DATABASE_URL")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Si GDAL/GEOS no están en la ruta estándar del sistema (no aplica en la imagen Docker).
GDAL_LIBRARY_PATH = env("GDAL_LIBRARY_PATH", default=None)
GEOS_LIBRARY_PATH = env("GEOS_LIBRARY_PATH", default=None)

AUTH_USER_MODEL = "cuentas.Usuario"
# RNF: contraseñas con PBKDF2-SHA256.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.PBKDF2PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    # JWT de simplejwt más el bloqueo de cambio de contraseña pendiente (DC-14).
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.cuentas.jwt.AutenticacionJWT"],
    # Todo error con solo `detail` lleva además `code` (p. ej. cambio_password_requerido, flota_en_uso).
    "EXCEPTION_HANDLER": "apps.comun.excepciones.error_con_codigo",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_RATES": {
        "login": env("THROTTLE_LOGIN", default="10/min"),
        # Portal público (HU-19), por IP: ráfaga y sostenido. Holgados porque en el aeropuerto muchos
        # pasajeros comparten IP (wifi, NAT); el control principal es el límite por teléfono.
        "portal_minuto": env("THROTTLE_PORTAL_MINUTO", default="20/min"),
        "portal_hora": env("THROTTLE_PORTAL_HORA", default="200/hour"),
    },
    # Proxies delante de Django (Nginx en producción = 1) para obtener la IP real del cliente.
    "NUM_PROXIES": int(env("DJANGO_NUM_PROXIES", default=""))
    if env("DJANGO_NUM_PROXIES", default="")
    else None,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
}

# Consultas de monitoreo por minuto: el nivel Personal de AeroAPI permite 10 conjuntos de resultados.
VUELOS_CONSULTAS_POR_MINUTO = env.int("VUELOS_CONSULTAS_POR_MINUTO", default=8)

# Celery: worker y beat. El broker usa otra base de Redis que la caché y los canales.
CELERY_BROKER_URL = env(
    "CELERY_BROKER_URL",
    default=env("REDIS_URL", default="redis://localhost:6379/0").rsplit("/", 1)[0] + "/1",
)
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_IGNORE_RESULT = True
CELERY_TASK_ACKS_LATE = True  # si el worker muere a medias, la tarea se entrega de nuevo
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
# Síncrono, sin worker: solo para medir o depurar. Devuelve el envío a la petición.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
# `expires` evita que se acumulen si el worker estuvo detenido: cada pasada revisa todo lo vencido.
CELERY_BEAT_SCHEDULE = {
    "expirar-solicitudes-rn06": {
        "task": "apps.reservas.tareas.expirar_solicitudes",
        "schedule": timedelta(seconds=60),
        "options": {"expires": 60},
    },
    "monitorear-vuelos-hu27": {
        "task": "apps.aeropuerto.tareas.monitorear_vuelos",
        "schedule": timedelta(seconds=60),
        "options": {"expires": 60},
    },
    "revisar-fila-hu29": {
        "task": "apps.aeropuerto.tareas.revisar_fila",
        "schedule": timedelta(seconds=60),
        "options": {"expires": 60},
    },
    "expirar-asignaciones-rn04": {
        "task": "apps.reservas.tareas.expirar_asignaciones",
        "schedule": timedelta(seconds=5),
        "options": {"expires": 5},
    },
}

# Caché compartida en Redis: contadores de throttling coherentes entre procesos (Gunicorn, workers).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/0"),
        "KEY_PREFIX": "flotaagil",
    }
}

# Portal (HU-19): máximo de solicitudes por teléfono y empresa en la ventana (alineado con RN-06).
PORTAL_MAX_SOLICITUDES_POR_TELEFONO = env.int("PORTAL_MAX_SOLICITUDES_POR_TELEFONO", default=3)
PORTAL_VENTANA_TELEFONO = timedelta(minutes=env.int("PORTAL_VENTANA_TELEFONO_MIN", default=15))

# Geocodificador (DC-05): sin clave se usa el de desarrollo (determinístico, sin servicios externos).
GOOGLE_GEOCODING_API_KEY = env("GOOGLE_GEOCODING_API_KEY", default="")
# Vuelos (HU-26): FlightAware AeroAPI si hay clave; si no, el consultor de desarrollo.
# Se validan las llegadas a AEROPUERTO_IATA.
FLIGHTAWARE_API_KEY = env("FLIGHTAWARE_API_KEY", default="")
AEROPUERTO_IATA = env("AEROPUERTO_IATA", default="SCL")

# WhatsApp (HU-20): Twilio si están todas; si no, el notificador de desarrollo (registra y deja en el log).
TWILIO_ACCOUNT_SID = env("TWILIO_ACCOUNT_SID", default="")
TWILIO_AUTH_TOKEN = env("TWILIO_AUTH_TOKEN", default="")
TWILIO_WHATSAPP_FROM = env("TWILIO_WHATSAPP_FROM", default="")  # +56…, número aprobado por Meta
TWILIO_PLANTILLA_VERIFICACION = env("TWILIO_PLANTILLA_VERIFICACION", default="")  # ContentSid HX…
# Avisos de estado (HU-21). Sin plantilla van como texto, que solo llega dentro de la ventana de 24 h.
TWILIO_PLANTILLA_AVISO_CONFIRMACION = env("TWILIO_PLANTILLA_AVISO_CONFIRMACION", default="")
TWILIO_PLANTILLA_AVISO_CONDUCTOR = env("TWILIO_PLANTILLA_AVISO_CONDUCTOR", default="")
TWILIO_PLANTILLA_AVISO_EN_CAMINO = env("TWILIO_PLANTILLA_AVISO_EN_CAMINO", default="")
TWILIO_PLANTILLA_AVISO_EN_ZONA = env("TWILIO_PLANTILLA_AVISO_EN_ZONA", default="")
TWILIO_PLANTILLA_AVISO_ENCUESTA = env("TWILIO_PLANTILLA_AVISO_ENCUESTA", default="")
# URL pública del backend con la que Twilio llama a los webhooks (y con la que se valida la firma).
WHATSAPP_URL_BASE = env("WHATSAPP_URL_BASE", default="")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MIN", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=env.int("JWT_REFRESH_HORAS", default=12)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "SIGNING_KEY": SECRET_KEY,
}

# RN-15: las posiciones GPS se conservan 30 días; la app no puede enviar posiciones más antiguas.
RETENCION_POSICIONES_DIAS = 30

# Contraseña temporal que genera el administrador (HU-10): vence si no se cambia en este plazo.
PASSWORD_TEMPORAL_HORAS = env.int("PASSWORD_TEMPORAL_HORAS", default=72)

# Panel web: el refresh viaja en una cookie httpOnly; el access se guarda solo en memoria.
JWT_COOKIE = {
    "nombre": "refresh_panel",
    "ruta": "/api/auth/",
    "samesite": "Lax",
    "secure": env.bool("JWT_COOKIE_SECURE", default=not DEBUG),
}

# Duración máxima de una sesión del panel desde el login, aunque se renueve.
# La app del conductor no la tiene.
JWT_SESION_MAX = timedelta(hours=env.int("JWT_SESION_MAX_HORAS", default=12))

# Orígenes desde los que el navegador puede llamar a login, refresh y logout del panel: comparación exacta
# con el encabezado Origin o, si falta, con el origen del Referer. Vacío = nadie entra al panel.
PANEL_ORIGENES = env.list("PANEL_ORIGENES", default=[])

# Bloqueo temporal al llegar a 5 intentos fallidos (USUARIO.intentos_fallidos).
LOGIN_MAX_INTENTOS = 5
LOGIN_BLOQUEO = timedelta(minutes=env.int("LOGIN_BLOQUEO_MIN", default=15))

# HU-25 (DC-27): link del convenio. Bloqueo por convenio y sesión que vence por inactividad.
CONVENIO_MAX_INTENTOS = env.int("CONVENIO_MAX_INTENTOS", default=5)
CONVENIO_BLOQUEO = timedelta(minutes=env.int("CONVENIO_BLOQUEO_MIN", default=15))
CONVENIO_SESION = timedelta(minutes=env.int("CONVENIO_SESION_MIN", default=120))

SPECTACULAR_SETTINGS = {
    "TITLE": "FlotaÁgil API",
    "DESCRIPTION": "API de FlotaÁgil: panel web, portal del pasajero y app del conductor.",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    # Nombres estables de los enums en el contrato (y en los tipos TypeScript generados).
    "ENUM_NAME_OVERRIDES": {
        "EstadoViajeEnum": "apps.reservas.models.EstadoViaje",
        "CanalEnum": "apps.reservas.models.Canal",
        "CanalPanelEnum": ["TELEFONO", "WHATSAPP", "CONVENIO"],
        "EstadoConductorEnum": "apps.flota.models.EstadoConductor",
        "TipoAlertaVueloEnum": "apps.aeropuerto.models.TipoAlertaVuelo",
        "DireccionMensajeEnum": "apps.reservas.models.DireccionMensaje",
        "EstadoConvenioEnum": "apps.convenios.models.EstadoConvenio",
    },
}

# Producción (TLS 1.2+ con HSTS en Nginx); se activan por entorno.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=0)
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
}


# HU-33 (DC-34): correo. `consola` en desarrollo; `ses` usa la interfaz SMTP de Amazon SES (sin dependencias).
CORREO_PROVEEDOR = env("CORREO_PROVEEDOR", default="consola")
DEFAULT_FROM_EMAIL = env("CORREO_REMITENTE", default="FlotaÁgil <no-responder@flotaagil.example>")
if CORREO_PROVEEDOR == "ses":
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = env("SES_SMTP_HOST", default="email-smtp.us-east-1.amazonaws.com")
    EMAIL_PORT = env.int("SES_SMTP_PUERTO", default=587)
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = env("SES_SMTP_USUARIO")
    EMAIL_HOST_PASSWORD = env("SES_SMTP_CLAVE")
    EMAIL_TIMEOUT = 10
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
