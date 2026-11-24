"""Permisos por rol y aislamiento por empresa (RN-13)."""

from rest_framework.permissions import BasePermission


class TieneRol(BasePermission):
    """Permite el acceso solo a usuarios autenticados con alguno de los roles indicados."""

    roles: frozenset[str] = frozenset()

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.rol in self.roles)


def con_roles(*roles: str) -> type[TieneRol]:
    """Clase de permiso para los roles dados: permission_classes = [con_roles(Rol.ADMINISTRADOR)]."""
    return type(f"TieneRol_{'_'.join(roles)}", (TieneRol,), {"roles": frozenset(roles)})


class TieneModulo(BasePermission):
    """HU-75 (DC-79): el administrador, siempre; el despachador, si tiene activo alguno de los módulos."""

    modulos: tuple[str, ...] = ()

    def has_permission(self, request, view):
        usuario = request.user
        return bool(usuario and usuario.is_authenticated and usuario.tiene_modulo(*self.modulos))


def con_modulo(*modulos: str) -> type[TieneModulo]:
    """Clase de permiso por módulo del panel: permission_classes = [con_modulo(Modulo.RESERVAS)]."""
    return type(f"TieneModulo_{'_'.join(modulos)}", (TieneModulo,), {"modulos": tuple(modulos)})


class ConModuloCuentas(BasePermission):
    """DC-51 (CC-22): las cuentas de pasajero y convenio solo existen si la empresa tiene el módulo.
    Sin él, sus endpoints responden 404, como si no existieran."""

    def has_permission(self, request, view):
        usuario = request.user
        if usuario and usuario.is_authenticated and not usuario.empresa.modulo_cuentas:
            from rest_framework.exceptions import NotFound

            raise NotFound("No disponible para esta empresa.", code="modulo_no_disponible")
        return True


class AisladoPorEmpresaMixin:
    """RN-13: el queryset se limita a la empresa del usuario y los registros nuevos se asignan a ella.

    Un registro de otra empresa no existe para el usuario: el detalle responde 404 y no 403,
    para no revelar que existe. `campo_empresa` permite filtrar por una relación
    (p. ej. "usuario__empresa").
    """

    campo_empresa = "empresa"

    def get_queryset(self):
        return super().get_queryset().filter(**{self.campo_empresa: self.request.user.empresa_id})

    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)
