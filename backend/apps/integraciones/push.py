"""HU-65 (CC-19, DC-62): Web Push con VAPID (RFC 8292) y contenido cifrado aes128gcm (RFC 8291 y RFC 8188).

Usa `cryptography` y PyJWT, que ya están instalados: no agrega dependencias. Las claves VAPID van en
`WEBPUSH_VAPID_PUBLICA` y `WEBPUSH_VAPID_PRIVADA` (P-256, base64url: el punto sin comprimir y el escalar de 32
bytes) y `WEBPUSH_CONTACTO` (mailto:). Sin claves, el envío queda desactivado y los avisos van por correo.

El envío corre en el worker (`apps.reservas.tareas.enviar_push`), con reintento ante fallas transitorias. Un
404 o 410 del servicio de push significa que la suscripción ya no existe: se borra.
"""

import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

import jwt
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

TAMANO_REGISTRO = 4096
VIGENCIA_S = 24 * 3600
TIEMPO_LIMITE_S = 10


class PushTransitorio(Exception):
    """Falla que puede resolverse reintentando (red, 429, 5xx)."""


class SuscripcionVencida(Exception):
    """El servicio de push respondió 404 o 410: la suscripción ya no sirve."""


def b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode()


def desde_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def configurado() -> bool:
    return bool(settings.WEBPUSH_VAPID_PUBLICA and settings.WEBPUSH_VAPID_PRIVADA)


def _hkdf(material: bytes, sal: bytes, info: bytes, largo: int) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=largo, salt=sal, info=info).derive(material)


def cifrar(contenido: bytes, p256dh: str, auth: str, *, sal: bytes | None = None, efimera=None) -> bytes:
    """Cuerpo aes128gcm para la suscripción (`p256dh` y `auth` del navegador, en base64url)."""
    publica_ua = desde_b64(p256dh)
    clave_ua = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), publica_ua)
    efimera = efimera or ec.generate_private_key(ec.SECP256R1())
    publica_as = efimera.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )
    secreto = efimera.exchange(ec.ECDH(), clave_ua)
    ikm = _hkdf(secreto, desde_b64(auth), b"WebPush: info\x00" + publica_ua + publica_as, 32)
    sal = sal or os.urandom(16)
    clave = _hkdf(ikm, sal, b"Content-Encoding: aes128gcm\x00", 16)
    nonce = _hkdf(ikm, sal, b"Content-Encoding: nonce\x00", 12)
    cifrado = AESGCM(clave).encrypt(nonce, contenido + b"\x02", None)
    encabezado = sal + TAMANO_REGISTRO.to_bytes(4, "big") + bytes([len(publica_as)]) + publica_as
    return encabezado + cifrado


def _clave_privada():
    escalar = int.from_bytes(desde_b64(settings.WEBPUSH_VAPID_PRIVADA), "big")
    return ec.derive_private_key(escalar, ec.SECP256R1())


def encabezado_vapid(endpoint: str, ahora: float | None = None) -> str:
    partes = urllib.parse.urlsplit(endpoint)
    reclamos = {
        "aud": f"{partes.scheme}://{partes.netloc}",
        "exp": int((ahora or time.time()) + 12 * 3600),
        "sub": settings.WEBPUSH_CONTACTO,
    }
    privada = _clave_privada().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    token = jwt.encode(reclamos, privada, algorithm="ES256")
    return f"vapid t={token}, k={settings.WEBPUSH_VAPID_PUBLICA}"


def enviar(endpoint: str, p256dh: str, auth: str, datos: dict) -> None:
    """Envía `datos` (JSON) a una suscripción. Lanza PushTransitorio o SuscripcionVencida."""
    cuerpo = cifrar(json.dumps(datos, ensure_ascii=False).encode(), p256dh, auth)
    peticion = urllib.request.Request(
        endpoint,
        data=cuerpo,
        method="POST",
        headers={
            "Content-Encoding": "aes128gcm",
            "Content-Type": "application/octet-stream",
            "TTL": str(VIGENCIA_S),
            "Urgency": "high",
            "Authorization": encabezado_vapid(endpoint),
        },
    )
    try:
        with urllib.request.urlopen(peticion, timeout=TIEMPO_LIMITE_S):
            return
    except urllib.error.HTTPError as error:
        if error.code in (404, 410):
            raise SuscripcionVencida(str(error.code)) from error
        if error.code == 429 or error.code >= 500:
            raise PushTransitorio(str(error.code)) from error
        raise
    except (urllib.error.URLError, TimeoutError, ConnectionError) as error:
        raise PushTransitorio(str(error)) from error
