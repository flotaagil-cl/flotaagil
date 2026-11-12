"""Notificaciones al pasajero por WhatsApp, detrás de un adaptador (HU-20, RN-06).

- `NotificadorDesarrollo`: no envía nada. Registra el mensaje en MENSAJE_WHATSAPP (con un SID `DEV-…`) y
  deja en el log un resumen con el número enmascarado. Las respuestas se simulan con
  `python manage.py simular_whatsapp <viaje> confirmar|cancelar`.
- `NotificadorTwilio`: Twilio WhatsApp Business API. La verificación usa una plantilla aprobada (Content API)
  con botones de respuesta rápida «Confirmar» y «Cancelar»; las respuestas llegan al webhook. Se usa cuando
  están `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM` y `WHATSAPP_URL_BASE`.
  Sin `TWILIO_PLANTILLA_VERIFICACION` (sandbox, que no admite plantillas propias) la verificación va como
  texto y el pasajero responde escribiendo «Confirmar» o «Cancelar»; solo llega si escribió en las
  últimas 24 h.

Los avisos de estado (HU-21) usan su plantilla si está configurada (`TWILIO_PLANTILLA_AVISO_*`); si no, van
como texto, que solo llega dentro de las 24 h desde el último mensaje del pasajero.

Todo mensaje (enviado o recibido) queda en MENSAJE_WHATSAPP. Los envíos corren en el worker
(`apps.reservas.tareas`). Si Twilio no responde tras los reintentos, el mensaje queda en FAILED y la solicitud
expira sola (RN-06).
"""

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Protocol

from django.conf import settings
from django.urls import reverse
from django.utils import timezone

logger = logging.getLogger(__name__)


def enmascarar_telefono(telefono: str | None) -> str:
    """El log no guarda el número completo (dato personal): +56900009001 → +569******01. Sin número (cuenta
    eliminada, DC-50), «sin teléfono»."""
    if not telefono:
        return "sin teléfono"
    return telefono[:4] + "*" * max(len(telefono) - 6, 0) + telefono[-2:]


def texto_verificacion(viaje, expira_en) -> tuple[str, dict]:
    """Cuerpo de la plantilla de verificación y sus variables (Twilio Content API: {{1}}…{{4}})."""
    variables = {
        "1": viaje.pasajero.nombre.split()[0],
        "2": viaje.empresa.razon_social,
        "3": timezone.localtime(viaje.recogida_en).strftime("%d-%m %H:%M"),
        "4": timezone.localtime(expira_en).strftime("%H:%M"),
    }
    cuerpo = (
        f"Hola {variables['1']}, {variables['2']} recibió tu solicitud de viaje para el {variables['3']}. "
        f"¿La confirmas? Responde antes de las {variables['4']}; si no, se anula. [Confirmar] [Cancelar]"
    )
    return cuerpo, variables


AVISO_CONFIRMACION = "confirmacion"
AVISO_CONDUCTOR = "conductor"
AVISO_EN_CAMINO = "en_camino"
AVISO_EN_ZONA = "en_zona"
AVISO_ENCUESTA = "encuesta"


def texto_aviso(viaje, tipo: str) -> tuple[str, dict]:
    """Cuerpo de un aviso de estado y sus variables (Twilio Content API: {{1}}, {{2}}…)."""
    nombre = viaje.pasajero.nombre.split()[0]
    if tipo == AVISO_CONFIRMACION:
        variables = {
            "1": nombre,
            "2": viaje.empresa.razon_social,
            "3": timezone.localtime(viaje.recogida_en).strftime("%d-%m %H:%M"),
        }
        cuerpo = (
            f"Hola {variables['1']}, {variables['2']} confirmó tu viaje para el {variables['3']}. "
            "Te avisaremos por aquí cuando tengas conductor. Si necesitas anularlo antes, responde Cancelar."
        )
    elif tipo == AVISO_CONDUCTOR:
        variables = {
            "1": nombre,
            "2": viaje.conductor.usuario.nombre,
            "3": viaje.vehiculo.marca_modelo,
            "4": viaje.vehiculo.patente,
        }
        cuerpo = (
            f"Hola {variables['1']}, tu conductor es {variables['2']}, en {variables['3']}, "
            f"patente {variables['4']}."
        )
    elif tipo == AVISO_EN_CAMINO:
        variables = {"1": viaje.conductor.usuario.nombre, "2": viaje.origen_dir}
        cuerpo = f"{variables['1']} va en camino a recogerte en {variables['2']}."
    elif tipo == AVISO_EN_ZONA:
        variables = {"1": viaje.origen_dir, "2": viaje.vehiculo.patente}
        cuerpo = f"Tu vehículo te espera en {variables['1']}. Patente {variables['2']}."
    elif tipo == AVISO_ENCUESTA:
        variables = {"1": nombre, "2": viaje.conductor.usuario.nombre}
        cuerpo = (
            f"Gracias por viajar con nosotros, {variables['1']}. ¿Cómo fue tu viaje con {variables['2']}? "
            "Responde con un número del 1 al 5. Es opcional."
        )
    else:
        raise ValueError(f"Aviso desconocido: {tipo}")
    return cuerpo, variables


class EnvioFallido(Exception):
    pass


class EnvioTransitorio(EnvioFallido):
    """Twilio no respondió o pidió esperar: se puede reintentar más tarde."""


class Notificador(Protocol):
    def solicitar_verificacion(self, viaje, expira_en) -> None: ...

    def responder(self, pasajero, viaje, texto: str) -> None: ...

    def avisar(self, viaje, tipo: str) -> None: ...

    def enviar_mensaje(self, mensaje) -> None: ...


def _registrar(pasajero, viaje, *, tipo: str, cuerpo: str, sid: str | None, estado: str):
    from apps.reservas.models import DireccionMensaje, MensajeWhatsapp

    return MensajeWhatsapp.objects.create(
        pasajero=pasajero,
        viaje=viaje,
        direccion=DireccionMensaje.SALIENTE,
        tipo=tipo,
        cuerpo=cuerpo[:1024],
        proveedor_sid=sid,
        estado_entrega=estado,
    )


class NotificadorDesarrollo:
    def enviar_mensaje(self, mensaje) -> None:
        from apps.reservas.models import EstadoEntrega

        mensaje.proveedor_sid = f"DEV-{uuid.uuid4().hex[:30]}"
        mensaje.estado_entrega = EstadoEntrega.SENT
        mensaje.save(update_fields=["proveedor_sid", "estado_entrega"])
        logger.info(
            "[WhatsApp simulado] Mensaje del chat a %s.", enmascarar_telefono(mensaje.pasajero.telefono)
        )

    def solicitar_verificacion(self, viaje, expira_en) -> None:
        from apps.reservas.models import EstadoEntrega, TipoMensaje

        cuerpo, _ = texto_verificacion(viaje, expira_en)
        _registrar(
            viaje.pasajero,
            viaje,
            tipo=TipoMensaje.PLANTILLA,
            cuerpo=cuerpo,
            sid=f"DEV-{uuid.uuid4().hex[:30]}",
            estado=EstadoEntrega.SENT,
        )
        logger.info(
            "[WhatsApp simulado] Verificación de la solicitud #%s a %s: recogida %s, expira %s.",
            viaje.pk,
            enmascarar_telefono(viaje.pasajero.telefono),
            timezone.localtime(viaje.recogida_en).strftime("%d-%m %H:%M"),
            timezone.localtime(expira_en).strftime("%H:%M"),
        )

    def responder(self, pasajero, viaje, texto: str) -> None:
        from apps.reservas.models import EstadoEntrega, TipoMensaje

        _registrar(
            pasajero,
            viaje,
            tipo=TipoMensaje.SESION,
            cuerpo=texto,
            sid=f"DEV-{uuid.uuid4().hex[:30]}",
            estado=EstadoEntrega.SENT,
        )
        logger.info("[WhatsApp simulado] Respuesta a %s: %s", enmascarar_telefono(pasajero.telefono), texto)

    def avisar(self, viaje, tipo: str) -> None:
        from apps.reservas.models import EstadoEntrega, TipoMensaje

        cuerpo, _ = texto_aviso(viaje, tipo)
        _registrar(
            viaje.pasajero,
            viaje,
            tipo=TipoMensaje.SESION,
            cuerpo=cuerpo,
            sid=f"DEV-{uuid.uuid4().hex[:30]}",
            estado=EstadoEntrega.SENT,
        )
        logger.info(
            "[WhatsApp simulado] Aviso «%s» del viaje #%s a %s.",
            tipo,
            viaje.pk,
            enmascarar_telefono(viaje.pasajero.telefono),
        )


class NotificadorTwilio:
    URL = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    # False mientras a la tarea le queden reintentos: la falla transitoria se propaga en vez de registrarse.
    definitivo = True

    def __init__(
        self,
        account_sid,
        auth_token,
        remitente,
        plantilla,
        url_base,
        plantillas_aviso=None,
        intentos=3,
        espera_base=0.5,
        timeout=5.0,
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.remitente = remitente
        self.plantilla = plantilla
        self.url_base = url_base.rstrip("/")
        self.plantillas_aviso = plantillas_aviso or {}
        self.intentos = intentos
        self.espera_base = espera_base
        self.timeout = timeout

    def _post(self, datos: dict) -> dict:
        credencial = base64.b64encode(f"{self.account_sid}:{self.auth_token}".encode()).decode()
        peticion = urllib.request.Request(
            self.URL.format(sid=self.account_sid),
            data=urllib.parse.urlencode(datos).encode(),
            headers={
                "Authorization": f"Basic {credencial}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )
        # La URL es fija y https; no se abren esquemas arbitrarios.
        with urllib.request.urlopen(peticion, timeout=self.timeout) as respuesta:  # nosec B310
            return json.load(respuesta)

    def _enviar(self, datos: dict) -> str:
        for intento in range(self.intentos):
            try:
                return self._post(datos)["sid"]
            except urllib.error.HTTPError as error:
                if error.code != 429 and error.code < 500:
                    raise EnvioFallido(f"Twilio respondió {error.code}.") from error
                logger.warning(
                    "Envío por WhatsApp falló (intento %s/%s): %s", intento + 1, self.intentos, error
                )
            except (urllib.error.URLError, TimeoutError) as error:
                logger.warning(
                    "Envío por WhatsApp falló (intento %s/%s): %s", intento + 1, self.intentos, error
                )
            if intento < self.intentos - 1:
                time.sleep(self.espera_base * 2**intento)  # reintento exponencial
        raise EnvioTransitorio("Twilio no está disponible.")

    def _comunes(self, telefono: str) -> dict:
        return {
            "From": f"whatsapp:{self.remitente}",
            "To": f"whatsapp:{telefono}",
            "StatusCallback": f"{self.url_base}{reverse('whatsapp-estado')}",
        }

    def _enviar_y_registrar(self, pasajero, viaje, *, tipo, cuerpo, datos):
        from apps.reservas.models import EstadoEntrega

        try:
            sid = self._enviar(datos)
        except EnvioFallido as error:
            if isinstance(error, EnvioTransitorio) and not self.definitivo:
                raise  # la tarea reintenta; todavía no es una falla
            logger.error("WhatsApp a %s no enviado: %s", enmascarar_telefono(pasajero.telefono), error)
            _registrar(pasajero, viaje, tipo=tipo, cuerpo=cuerpo, sid=None, estado=EstadoEntrega.FAILED)
            return
        _registrar(pasajero, viaje, tipo=tipo, cuerpo=cuerpo, sid=sid, estado=EstadoEntrega.QUEUED)

    def solicitar_verificacion(self, viaje, expira_en) -> None:
        from apps.reservas.models import TipoMensaje

        cuerpo, variables = texto_verificacion(viaje, expira_en)
        if not self.plantilla:
            # Sandbox: mensaje de sesión con la misma pregunta, a responder por escrito.
            texto = cuerpo.replace("[Confirmar] [Cancelar]", "Escribe Confirmar o Cancelar.")
            datos = self._comunes(viaje.pasajero.telefono) | {"Body": texto}
            self._enviar_y_registrar(
                viaje.pasajero, viaje, tipo=TipoMensaje.SESION, cuerpo=texto, datos=datos
            )
            return
        datos = self._comunes(viaje.pasajero.telefono) | {
            "ContentSid": self.plantilla,
            "ContentVariables": json.dumps(variables, ensure_ascii=False),
        }
        self._enviar_y_registrar(
            viaje.pasajero, viaje, tipo=TipoMensaje.PLANTILLA, cuerpo=cuerpo, datos=datos
        )

    def enviar_mensaje(self, mensaje) -> None:
        """HU-30: el mensaje ya está registrado; aquí queda con su SID o, si no se pudo, en FAILED."""
        from apps.reservas.models import EstadoEntrega

        datos = self._comunes(mensaje.pasajero.telefono) | {"Body": mensaje.cuerpo}
        try:
            mensaje.proveedor_sid = self._enviar(datos)
        except EnvioFallido as error:
            if isinstance(error, EnvioTransitorio) and not self.definitivo:
                raise  # la tarea reintenta; todavía no es una falla
            logger.error(
                "WhatsApp a %s no enviado: %s", enmascarar_telefono(mensaje.pasajero.telefono), error
            )
            mensaje.estado_entrega = EstadoEntrega.FAILED
            mensaje.save(update_fields=["estado_entrega"])
            return
        mensaje.save(update_fields=["proveedor_sid"])

    def responder(self, pasajero, viaje, texto: str) -> None:
        """Mensaje de sesión: solo dentro de las 24 h desde el último mensaje del pasajero (regla de
        WhatsApp)."""
        from apps.reservas.models import TipoMensaje

        datos = self._comunes(pasajero.telefono) | {"Body": texto}
        self._enviar_y_registrar(pasajero, viaje, tipo=TipoMensaje.SESION, cuerpo=texto, datos=datos)

    def avisar(self, viaje, tipo: str) -> None:
        from apps.reservas.models import TipoMensaje

        cuerpo, variables = texto_aviso(viaje, tipo)
        datos = self._comunes(viaje.pasajero.telefono)
        plantilla = self.plantillas_aviso.get(tipo)
        if plantilla:
            datos |= {"ContentSid": plantilla, "ContentVariables": json.dumps(variables, ensure_ascii=False)}
            tipo_mensaje = TipoMensaje.PLANTILLA
        else:
            datos |= {"Body": cuerpo}
            tipo_mensaje = TipoMensaje.SESION
        self._enviar_y_registrar(viaje.pasajero, viaje, tipo=tipo_mensaje, cuerpo=cuerpo, datos=datos)


def firma_twilio(auth_token: str, url: str, parametros: dict) -> str:
    """Firma X-Twilio-Signature: HMAC-SHA1 de la URL más los parámetros POST ordenados, en base64."""
    datos = url + "".join(f"{clave}{parametros[clave]}" for clave in sorted(parametros))
    return base64.b64encode(hmac.new(auth_token.encode(), datos.encode(), hashlib.sha1).digest()).decode()


def firma_valida(auth_token: str, url: str, parametros: dict, firma: str) -> bool:
    return hmac.compare_digest(firma_twilio(auth_token, url, parametros), firma or "")


def twilio_configurado() -> bool:
    return all(
        getattr(settings, nombre, "")
        for nombre in (
            "TWILIO_ACCOUNT_SID",
            "TWILIO_AUTH_TOKEN",
            "TWILIO_WHATSAPP_FROM",
            "WHATSAPP_URL_BASE",
        )
    )


def obtener_notificador() -> Notificador:
    if twilio_configurado():
        return NotificadorTwilio(
            settings.TWILIO_ACCOUNT_SID,
            settings.TWILIO_AUTH_TOKEN,
            settings.TWILIO_WHATSAPP_FROM,
            settings.TWILIO_PLANTILLA_VERIFICACION,
            settings.WHATSAPP_URL_BASE,
            intentos=1,  # los reintentos los hace la tarea de Celery, con espera exponencial
            plantillas_aviso={
                AVISO_CONFIRMACION: settings.TWILIO_PLANTILLA_AVISO_CONFIRMACION,
                AVISO_CONDUCTOR: settings.TWILIO_PLANTILLA_AVISO_CONDUCTOR,
                AVISO_EN_CAMINO: settings.TWILIO_PLANTILLA_AVISO_EN_CAMINO,
                AVISO_EN_ZONA: settings.TWILIO_PLANTILLA_AVISO_EN_ZONA,
                AVISO_ENCUESTA: settings.TWILIO_PLANTILLA_AVISO_ENCUESTA,
            },
        )
    return NotificadorDesarrollo()
