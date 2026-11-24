"""CC-23 (HU-72, DC-75): pase de convenio del portal base, con correo + clave.

Sin módulo de cuentas, la empresa cliente pide con la clave que recibió su contacto al aprobarse el convenio
(DC-74). El correo debe ser el contacto o uno autorizado (`Convenio.habilita`, D5): con eso se ubica el
convenio.
Si calza, se entrega un pase firmado (`TimestampSigner`, sal propia) con `convenio:clave_version:correo`, que
vale `convenio_pase_vigencia_min` y se revalida en cada uso: regenerar o revocar la clave y desactivar el
convenio lo invalidan al instante (RN-08).

Cualquier fallo responde lo mismo (no se revela si el correo existe). Límites en la caché: por IP y hora, y
bloqueo temporal por correo tras `convenio_pase_max_fallos` claves erradas, con auditoría BLOQUEO_CLAVE sin
usuario (como DC-27). La clave nunca se registra ni se devuelve.
"""

from django.contrib.auth.hashers import check_password, make_password
from django.core import signing
from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import APIException, Throttled

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.convenios.models import Convenio, EstadoConvenio
from apps.convenios.servicios import clave_correcta, normalizar_clave

SAL_PASE = "pase-convenio"
# Hash de relleno: con un correo sin convenio se compara igual, para que la respuesta no tarde distinto.
_HASH_RELLENO = None


class ClaveInvalida(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_code = "clave_invalida"
    default_detail = "El correo o la clave no son válidos para un convenio vigente."


class ClaveBloqueada(Throttled):
    default_code = "clave_bloqueada"
    default_detail = "Demasiados intentos con este correo. Espera unos minutos e intenta de nuevo."


class LimitePaseIP(Throttled):
    default_code = "limite_ip"
    default_detail = "Se hicieron demasiados intentos desde esta conexión. Espera un rato e intenta de nuevo."


class PaseVencido(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "pase_vencido"
    default_detail = "Tu acceso de convenio venció. Ingresa de nuevo tu correo y la clave."


class PaseInvalido(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_code = "pase_invalido"
    default_detail = "Tu acceso de convenio ya no es válido. Ingresa de nuevo tu correo y la clave."


def _relleno() -> str:
    global _HASH_RELLENO
    if _HASH_RELLENO is None:
        _HASH_RELLENO = make_password("relleno-sin-convenio")
    return _HASH_RELLENO


def _clave_cache(tipo: str, empresa, valor: str) -> str:
    return f"pase_convenio:{tipo}:{empresa.pk}:{valor}"


def _verificar_limite_ip(empresa, ip: str | None) -> None:
    if not ip:
        return
    clave = _clave_cache("ip", empresa, ip)
    cache.add(clave, 0, timeout=3600)
    if cache.incr(clave) > empresa.configuracion.reserva_publica_max_ip_hora:
        raise LimitePaseIP(wait=3600)


def _candidatos(empresa, correo: str) -> list[Convenio]:
    convenios = Convenio.objects.select_related("empresa").filter(
        empresa=empresa,
        estado=EstadoConvenio.APROBADO,
        usuario__isnull=True,
        clave_hash__isnull=False,
    )
    return [convenio for convenio in convenios if convenio.habilita(correo)]


def _registrar_fallo(empresa, correo: str, candidatos: list[Convenio]) -> None:
    config = empresa.configuracion
    segundos = config.convenio_pase_bloqueo_min * 60
    fallos = _clave_cache("fallos", empresa, correo)
    cache.add(fallos, 0, timeout=segundos)
    if cache.incr(fallos) >= config.convenio_pase_max_fallos:
        cache.set(_clave_cache("bloqueo", empresa, correo), 1, timeout=segundos)
        cache.delete(fallos)
        for convenio in candidatos:  # DC-27: sin usuario autenticado
            auditoria.registrar(
                usuario=None,
                empresa_id=empresa.pk,
                entidad=Entidad.CONVENIO,
                entidad_id=convenio.pk,
                accion="BLOQUEO_CLAVE",
                motivo=f"{config.convenio_pase_max_fallos} claves erradas seguidas desde el portal.",
            )


def emitir(empresa, correo: str, clave: str, ip: str | None = None) -> tuple[str, Convenio, str]:
    """Devuelve (pase, convenio, correo normalizado). Mismo 400 para clave mala, correo no habilitado o
    convenio que no está aprobado (D5)."""
    correo = (correo or "").strip().lower()
    _verificar_limite_ip(empresa, ip)
    if cache.get(_clave_cache("bloqueo", empresa, correo)):
        raise ClaveBloqueada(wait=empresa.configuracion.convenio_pase_bloqueo_min * 60)
    candidatos = _candidatos(empresa, correo)
    convenio = next((c for c in candidatos if clave_correcta(c, clave)), None)
    if not candidatos:
        check_password(normalizar_clave(clave), _relleno())
    if convenio is None:
        _registrar_fallo(empresa, correo, candidatos)
        raise ClaveInvalida()
    cache.delete(_clave_cache("fallos", empresa, correo))
    pase = signing.TimestampSigner(salt=SAL_PASE).sign(f"{convenio.pk}:{convenio.clave_version}:{correo}")
    return pase, convenio, correo


def validar(empresa, pase: str) -> tuple[Convenio, str]:
    """Revalida el pase en cada uso: vigencia, versión de la clave, estado del convenio y correo
    (RN-08, RN-13)."""
    firmador = signing.TimestampSigner(salt=SAL_PASE)
    try:
        contenido = firmador.unsign(pase, max_age=empresa.configuracion.convenio_pase_vigencia_min * 60)
    except signing.SignatureExpired as error:
        raise PaseVencido() from error
    except signing.BadSignature as error:
        raise PaseInvalido() from error
    try:
        pk, version, correo = contenido.split(":", 2)
        pk, version = int(pk), int(version)
    except ValueError as error:
        raise PaseInvalido() from error
    convenio = (
        Convenio.objects.select_related("empresa")
        .filter(pk=pk, empresa=empresa, estado=EstadoConvenio.APROBADO, usuario__isnull=True)
        .first()
    )
    if (
        convenio is None
        or not convenio.clave_hash
        or convenio.clave_version != version
        or not convenio.habilita(correo)
    ):
        raise PaseInvalido()
    return convenio, correo
