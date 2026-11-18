"""HU-65 (CC-19, DC-62): estados del viaje para el pasajero con cuenta: en vivo, Web Push (VAPID) o correo."""

import json
import urllib.error

import jwt
import pytest
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.core import mail
from django.urls import reverse

from apps.auditoria.models import Auditoria
from apps.cuentas.tests.fabricas import UsuarioFactory
from apps.flota.tests.test_mapa_ws import access
from apps.integraciones import push
from apps.reservas import avisos_pasajero, tareas
from apps.reservas.models import CuentaPasajero, EstadoViaje, SuscripcionPush, Viaje
from apps.reservas.tests.fabricas import ViajeFactory
from apps.reservas.tests.test_cuenta_pasajero import activar, crear_cuenta, entrar
from apps.reservas.tipos_aviso import AVISO_CONDUCTOR, AVISO_CONFIRMACION, AVISO_EN_ZONA
from config.asgi import application

E = EstadoViaje
ENDPOINT = "https://fcm.googleapis.com/fcm/send/abc123"


def b64(datos: bytes) -> str:
    return push.b64(datos)


def par_p256():
    privada = ec.generate_private_key(ec.SECP256R1())
    publica = privada.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    return privada, publica


@pytest.fixture
def vapid(settings):
    privada, publica = par_p256()
    settings.WEBPUSH_VAPID_PRIVADA = b64(privada.private_numbers().private_value.to_bytes(32, "big"))
    settings.WEBPUSH_VAPID_PUBLICA = b64(publica)
    return privada, publica


@pytest.fixture
def navegador():
    """Las claves que entrega el navegador al suscribirse (p256dh y auth) y su privada, para descifrar."""
    privada, publica = par_p256()
    auth = b"secreto-auth-16b"
    return {"privada": privada, "p256dh": b64(publica), "auth": b64(auth)}


def descifrar(cuerpo: bytes, navegador: dict) -> bytes:
    """Lo que hace el navegador al recibir el push (RFC 8291), para comprobar el cifrado."""
    sal, largo_id = cuerpo[:16], cuerpo[20]
    publica_as = cuerpo[21 : 21 + largo_id]
    cifrado = cuerpo[21 + largo_id :]
    clave_as = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), publica_as)
    secreto = navegador["privada"].exchange(ec.ECDH(), clave_as)
    publica_ua = push.desde_b64(navegador["p256dh"])

    def hkdf(material, salt, info, largo):
        return HKDF(algorithm=hashes.SHA256(), length=largo, salt=salt, info=info).derive(material)

    ikm = hkdf(secreto, push.desde_b64(navegador["auth"]), b"WebPush: info\x00" + publica_ua + publica_as, 32)
    clave = hkdf(ikm, sal, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = hkdf(ikm, sal, b"Content-Encoding: nonce\x00", 12)
    claro = AESGCM(clave).decrypt(nonce, cifrado, None)
    assert claro.endswith(b"\x02")
    return claro[:-1]


class RespuestaFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def servicio_push(monkeypatch):
    """El servicio de push del navegador: guarda cada petición y responde lo que se programe."""
    enviadas, respuestas = [], []

    def urlopen(peticion, timeout):
        enviadas.append(peticion)
        if respuestas:
            respuesta = respuestas.pop(0)
            if isinstance(respuesta, Exception):
                raise respuesta
        return RespuestaFalsa()

    monkeypatch.setattr(push.urllib.request, "urlopen", urlopen)
    return enviadas, respuestas


def error_http(codigo):
    return urllib.error.HTTPError(ENDPOINT, codigo, "x", {}, None)


class TestWebPush:
    def test_cifrado_aes128gcm_que_el_navegador_descifra(self, navegador):
        cuerpo = push.cifrar(json.dumps({"titulo": "Hola"}).encode(), navegador["p256dh"], navegador["auth"])
        assert int.from_bytes(cuerpo[16:20], "big") == push.TAMANO_REGISTRO
        assert json.loads(descifrar(cuerpo, navegador)) == {"titulo": "Hola"}

    def test_vapid_firmado_para_el_origen_del_servicio(self, vapid, settings):
        _, publica = vapid
        encabezado = push.encabezado_vapid(ENDPOINT, ahora=1_000_000)
        token = encabezado.split("t=")[1].split(",")[0]
        assert encabezado.endswith(f"k={settings.WEBPUSH_VAPID_PUBLICA}")
        clave = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), publica)
        reclamos = jwt.decode(
            token,
            clave,
            algorithms=["ES256"],
            audience="https://fcm.googleapis.com",
            options={"verify_exp": False},
        )
        assert (reclamos["sub"], reclamos["exp"]) == (settings.WEBPUSH_CONTACTO, 1_000_000 + 12 * 3600)

    def test_envio_y_errores(self, vapid, navegador, servicio_push):
        enviadas, respuestas = servicio_push
        push.enviar(ENDPOINT, navegador["p256dh"], navegador["auth"], {"titulo": "Llegó"})
        peticion = enviadas[0]
        assert (peticion.full_url, peticion.get_header("Content-encoding"), peticion.get_header("Ttl")) == (
            ENDPOINT,
            "aes128gcm",
            "86400",
        )
        assert json.loads(descifrar(peticion.data, navegador)) == {"titulo": "Llegó"}
        for error, esperado in (
            (error_http(410), push.SuscripcionVencida),
            (error_http(404), push.SuscripcionVencida),
            (error_http(503), push.PushTransitorio),
            (error_http(429), push.PushTransitorio),
            (urllib.error.URLError("sin red"), push.PushTransitorio),
            (error_http(400), urllib.error.HTTPError),
        ):
            respuestas.append(error)
            with pytest.raises(esperado):
                push.enviar(ENDPOINT, navegador["p256dh"], navegador["auth"], {})

    def test_solo_https(self, navegador):
        with pytest.raises(ValueError):
            push.enviar("http://fcm.googleapis.com/x", navegador["p256dh"], navegador["auth"], {})

    def test_sin_claves_no_esta_configurado(self, settings):
        settings.WEBPUSH_VAPID_PUBLICA = settings.WEBPUSH_VAPID_PRIVADA = ""
        assert not push.configurado()


@pytest.fixture
def activa(cliente, empresa, twilio, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        crear_cuenta(cliente, empresa)
    activar(cliente, empresa)
    web, _ = entrar()
    mail.outbox.clear()
    return web


def pedir(web):
    from apps.reservas.tests.test_cuenta_pasajero import TestReservas

    assert (
        web.post(reverse("mi-cuenta-solicitudes"), TestReservas().solicitud(), format="json").status_code
        == 201
    )
    return Viaje.objects.order_by("-pk").first()


def suscribir(web, navegador):
    datos = {"endpoint": ENDPOINT, "keys": {"p256dh": navegador["p256dh"], "auth": navegador["auth"]}}
    return web.post(reverse("mi-cuenta-push"), datos, format="json")


@pytest.mark.django_db
class TestAvisosDelViaje:
    def test_web_push_cuando_lo_acepto(self, activa, vapid, navegador, servicio_push, twilio):
        enviadas, _ = servicio_push
        assert suscribir(activa, navegador).status_code == 201
        viaje = pedir(activa)
        tareas.enviar_aviso(viaje.pk, AVISO_EN_ZONA)
        datos = json.loads(descifrar(enviadas[0].data, navegador))
        assert datos == {
            "titulo": "Tu conductor llegó",
            "cuerpo": "Tu conductor llegó al punto de recogida.",
            "url": f"/mis-viajes/{viaje.pk}",
        }
        assert mail.outbox == [] and twilio.enviados == []

    def test_suscripcion_vencida_se_borra(self, activa, vapid, navegador, servicio_push):
        _, respuestas = servicio_push
        suscribir(activa, navegador)
        respuestas.append(error_http(410))
        tareas.enviar_aviso(pedir(activa).pk, AVISO_EN_ZONA)
        assert not SuscripcionPush.objects.exists()

    def test_sin_push_va_por_correo_solo_con_la_casilla(self, activa, settings, twilio):
        settings.WEBPUSH_VAPID_PUBLICA = ""
        viaje = pedir(activa)
        Viaje.objects.filter(pk=viaje.pk).update(estado=E.CANCELADO, motivo_cancelacion="Prueba")
        tareas.enviar_aviso(viaje.pk, "cancelacion")
        assert mail.outbox == []  # sin la casilla no sale el correo del viaje
        assert (
            activa.patch(reverse("mi-cuenta"), {"acepta_avisos_correo": True}, format="json").status_code
            == 200
        )
        assert Auditoria.objects.filter(
            accion="EDITAR_PERFIL", datos_previos={"campos": ["acepta_avisos_correo"]}
        )
        tareas.enviar_aviso(viaje.pk, "cancelacion")
        assert (mail.outbox[0].to, mail.outbox[0].subject) == (["paula@correo.example"], "Viaje cancelado")
        assert twilio.enviados == []

    def test_conductor_asignado_con_vehiculo(self, activa, empresa, settings):
        from apps.reservas.tests.fabricas import ConductorFactory, VehiculoFactory

        settings.WEBPUSH_VAPID_PUBLICA = ""
        CuentaPasajero.objects.update(acepta_avisos_correo=True)
        viaje = pedir(activa)
        vehiculo = VehiculoFactory(empresa=empresa, patente="BCDF10", marca_modelo="Toyota Yaris")
        conductor = ConductorFactory(
            usuario__empresa=empresa, usuario__nombre="Pedro Soto", vehiculo_activo=vehiculo
        )
        Viaje.objects.filter(pk=viaje.pk).update(conductor=conductor, estado=E.ACEPTADO)
        tareas.enviar_aviso(viaje.pk, AVISO_CONDUCTOR)
        assert "Pedro Soto irá a buscarte (Toyota Yaris, patente BCDF10)." in mail.outbox[0].body

    def test_otros_avisos_no_salen_para_la_cuenta(self, activa, twilio):
        CuentaPasajero.objects.update(acepta_avisos_correo=True)
        tareas.enviar_aviso(pedir(activa).pk, AVISO_CONFIRMACION)
        assert mail.outbox == [] and twilio.enviados == []

    def test_viaje_de_invitado_del_mismo_numero_no_avisa_a_la_cuenta(self, activa, empresa, settings, twilio):
        """DC-65: la cuenta sin teléfono verificado no recibe avisos de viajes que no pidió."""
        settings.WEBPUSH_VAPID_PUBLICA = ""
        cuenta = CuentaPasajero.objects.get()
        CuentaPasajero.objects.update(acepta_avisos_correo=True)
        ajeno = ViajeFactory(empresa=empresa, pasajero=cuenta.pasajero, estado=E.EN_ZONA)
        assert avisos_pasajero.enviar(ajeno, AVISO_EN_ZONA) is False  # sigue el camino de los invitados
        assert mail.outbox == []


@pytest.mark.django_db
class TestSuscripcion:
    def test_clave_publica(self, activa, vapid, settings):
        assert activa.get(reverse("mi-cuenta-push")).data == {"clave_publica": settings.WEBPUSH_VAPID_PUBLICA}
        settings.WEBPUSH_VAPID_PRIVADA = ""
        assert activa.get(reverse("mi-cuenta-push")).data == {"clave_publica": None}

    @pytest.mark.parametrize(
        "endpoint",
        [
            "http://fcm.googleapis.com/x",
            "https://intranet.example/x",
            "https://fcm.googleapis.com.malo.example/x",
        ],
    )
    def test_solo_servicios_de_push_conocidos(self, activa, navegador, endpoint):
        datos = {"endpoint": endpoint, "keys": {"p256dh": navegador["p256dh"], "auth": navegador["auth"]}}
        respuesta = activa.post(reverse("mi-cuenta-push"), datos, format="json")
        assert respuesta.status_code == 400
        assert not SuscripcionPush.objects.exists()

    def test_guardar_quitar_y_eliminar_la_cuenta(self, activa, navegador):
        assert (
            activa.post(reverse("mi-cuenta-push"), {"endpoint": ENDPOINT}, format="json").status_code == 400
        )
        assert suscribir(activa, navegador).status_code == 201
        assert suscribir(activa, navegador).status_code == 201  # el mismo navegador no se duplica
        assert SuscripcionPush.objects.count() == 1
        assert (
            activa.delete(reverse("mi-cuenta-push"), {"endpoint": ENDPOINT}, format="json").status_code == 204
        )
        assert not SuscripcionPush.objects.exists()
        suscribir(activa, navegador)
        assert activa.delete(reverse("mi-cuenta")).status_code == 204
        assert not SuscripcionPush.objects.exists()

    def test_solo_el_pasajero(self, panel, despachador):
        panel.force_authenticate(despachador)
        assert panel.get(reverse("mi-cuenta-push")).status_code == 403

    def test_casilla_al_crear_la_cuenta(self, cliente, empresa):
        crear_cuenta(cliente, empresa, acepta_avisos_correo=True)
        assert CuentaPasajero.objects.get().acepta_avisos_correo is True


@pytest.mark.django_db(transaction=True)
def test_tu_viaje_en_vivo_por_el_canal(cliente, empresa, otra_empresa, django_capture_on_commit_callbacks):
    """El pasajero con cuenta recibe el cambio de estado; sin el módulo de cuentas no se conecta."""
    from apps.reservas import estados

    with django_capture_on_commit_callbacks(execute=True):
        crear_cuenta(cliente, empresa)
    activar(cliente, empresa)
    web, _ = entrar()
    viaje = pedir(web)
    usuario = CuentaPasajero.objects.get().usuario
    sin_modulo = UsuarioFactory(empresa=otra_empresa, rol="PASAJERO")
    otra_empresa.modulo_cuentas = False
    otra_empresa.save()

    @database_sync_to_async
    def cancelar():
        estados.transicionar(viaje, E.CANCELADO, actor="DESPACHADOR", motivo_cancelacion="x")

    async def escenario():
        rechazado = WebsocketCommunicator(
            application, "/ws/chat/", subprotocols=["flotaagil", access(sin_modulo)]
        )
        assert (await rechazado.connect()) == (False, 4403)
        ws = WebsocketCommunicator(application, "/ws/chat/", subprotocols=["flotaagil", access(usuario)])
        assert (await ws.connect())[0]
        await ws.receive_json_from()
        await cancelar()
        evento = await ws.receive_json_from(timeout=2)
        await ws.disconnect()
        return evento

    assert async_to_sync(escenario)() == {"tipo": "viaje", "viaje": viaje.pk, "estado": E.CANCELADO}
