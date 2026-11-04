"""Administración de convenios (HU-11). RN-08: desactivar invalida el link sin afectar el historial.
RN-12: los cambios de contraseña o de estado generan auditoría inmutable.

La contraseña la genera el servidor y se entrega una sola vez, igual que las temporales de HU-10 (DC-24): solo
se guarda su hash, y ni ella ni el hash llegan a la auditoría ni a los logs.
"""

from django.db import transaction

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.cuentas.credenciales import nueva_password_temporal

from .models import Convenio


def _auditar(usuario, convenio: Convenio, accion: str, datos_previos: dict | None = None) -> None:
    auditoria.registrar(
        usuario=usuario,
        entidad=Entidad.CONVENIO,
        entidad_id=convenio.pk,
        accion=accion,
        datos_previos=datos_previos,
    )


@transaction.atomic
def crear(empresa, datos: dict, *, usuario) -> tuple[Convenio, str]:
    password = nueva_password_temporal()
    convenio = Convenio(empresa=empresa, **datos)
    convenio.set_password(password)
    convenio.save()
    _auditar(usuario, convenio, "CREACION")
    return convenio, password


@transaction.atomic
def editar(convenio: Convenio, datos: dict, *, usuario) -> Convenio:
    convenio = Convenio.objects.select_for_update().get(pk=convenio.pk)
    previos = {campo: getattr(convenio, campo) for campo in datos if getattr(convenio, campo) != datos[campo]}
    if not previos:
        return convenio
    for campo, valor in datos.items():
        setattr(convenio, campo, valor)
    convenio.save(update_fields=list(previos))
    if "activo" in previos:
        _auditar(usuario, convenio, "ACTIVACION" if convenio.activo else "DESACTIVACION")  # RN-12
    otros = {campo: valor for campo, valor in previos.items() if campo != "activo"}
    if otros:
        _auditar(usuario, convenio, "EDICION", otros)
    return convenio


@transaction.atomic
def rotar_password(convenio: Convenio, *, usuario) -> str:
    """La anterior deja de servir en el mismo momento. Devuelve la nueva: no se puede volver a consultar."""
    convenio = Convenio.objects.select_for_update().get(pk=convenio.pk)
    password = nueva_password_temporal()
    convenio.set_password(password)
    # Con la contraseña nueva, un bloqueo por intentos con la anterior ya no tiene sentido.
    convenio.intentos_fallidos, convenio.bloqueado_hasta = 0, None
    convenio.save(update_fields=["password_hash", "intentos_fallidos", "bloqueado_hasta"])
    _auditar(usuario, convenio, "CAMBIO_CLAVE")  # RN-12
    return password
