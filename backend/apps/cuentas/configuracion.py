"""Configuración de la empresa en el panel (CC-19, validación de DC-66; DC-68): solo el administrador.

Números de la central para los botones de emergencia del portal (DC-62) y los parámetros de la reserva pública
que antes solo se cambiaban en el admin de Django: plazos de confirmación (DC-53), cierre de las «Sin
confirmar» (DC-59) y límites antispam (DC-59). Cada valor tiene un mínimo y un máximo; cada cambio queda en
AUDITORIA con los valores anteriores. El interruptor `modulo_cuentas` sigue siendo solo del superusuario
(admin de Django).
"""

from django.core.exceptions import ValidationError as ErrorDeDjango
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Entidad
from apps.auditoria.servicios import registrar
from apps.comun.permisos import con_roles
from apps.comun.validadores import normalizar_telefono, validar_telefono_e164

from .models import ConfiguracionEmpresa, Rol

# DC-68: (mínimo, máximo) de cada parámetro numérico.
RANGOS = {
    "confirmacion_antes_horas": (1, 168),
    "confirmacion_plazo_corto_min": (10, 240),
    "cierre_no_confirmada_horas": (1, 48),
    "reserva_publica_max_ip_hora": (5, 500),
    "reserva_publica_max_correo_hora": (1, 50),
    "reserva_publica_max_convenio_hora": (1, 500),
}
TELEFONOS = ("telefono_central", "whatsapp_central")


def _numero(campo: str, ayuda: str):
    minimo, maximo = RANGOS[campo]
    return serializers.IntegerField(
        min_value=minimo, max_value=maximo, help_text=f"{ayuda} ({minimo} a {maximo})."
    )


class ConfiguracionEmpresaSerializer(serializers.ModelSerializer):
    confirmacion_antes_horas = _numero(
        "confirmacion_antes_horas", "Horas antes de la recogida para confirmar"
    )
    confirmacion_plazo_corto_min = _numero("confirmacion_plazo_corto_min", "Minutos si falta menos que eso")
    cierre_no_confirmada_horas = _numero("cierre_no_confirmada_horas", "Horas tras la recogida para cerrar")
    reserva_publica_max_ip_hora = _numero("reserva_publica_max_ip_hora", "Solicitudes por IP y hora")
    reserva_publica_max_correo_hora = _numero(
        "reserva_publica_max_correo_hora", "Solicitudes por correo y hora"
    )
    reserva_publica_max_convenio_hora = _numero(
        "reserva_publica_max_convenio_hora", "Por correo de convenio y hora"
    )

    class Meta:
        model = ConfiguracionEmpresa
        fields = [*TELEFONOS, *RANGOS]
        extra_kwargs = {
            campo: {"required": False, "allow_blank": True, "validators": []} for campo in TELEFONOS
        }

    def _telefono(self, valor):
        valor = normalizar_telefono(valor or "")
        if valor:
            try:
                validar_telefono_e164(valor)
            except ErrorDeDjango as error:
                raise serializers.ValidationError(
                    "Número en formato internacional, p. ej. +56912345678."
                ) from error
        return valor

    def validate_telefono_central(self, valor):
        return self._telefono(valor)

    def validate_whatsapp_central(self, valor):
        return self._telefono(valor)

    def validate(self, datos):
        # DC-68: el plazo corto se usa cuando falta menos que el plazo normal; debe ser menor que él.
        def valor(campo):
            return datos.get(campo, getattr(self.instance, campo, None))

        horas, corto = valor("confirmacion_antes_horas"), valor("confirmacion_plazo_corto_min")
        if horas is not None and corto is not None and corto >= horas * 60:
            raise serializers.ValidationError(
                {
                    "confirmacion_plazo_corto_min": (
                        f"Debe ser menor que el plazo para confirmar ({horas} h = {horas * 60} min)."
                    )
                }
            )
        return datos


class ConfiguracionEmpresaView(APIView):
    permission_classes = [con_roles(Rol.ADMINISTRADOR)]

    def _configuracion(self, request) -> ConfiguracionEmpresa:
        return ConfiguracionEmpresa.objects.select_for_update().get(empresa_id=request.user.empresa_id)

    @extend_schema(
        tags=["configuracion"],
        summary="Configuración de mi empresa",
        responses=ConfiguracionEmpresaSerializer,
    )
    def get(self, request):
        configuracion = ConfiguracionEmpresa.objects.get(empresa_id=request.user.empresa_id)
        return Response(ConfiguracionEmpresaSerializer(configuracion).data)

    @extend_schema(
        tags=["configuracion"],
        summary="Cambiar la configuración de mi empresa (auditado)",
        request=ConfiguracionEmpresaSerializer,
        responses=ConfiguracionEmpresaSerializer,
    )
    def patch(self, request):
        with transaction.atomic():
            configuracion = self._configuracion(request)
            entrada = ConfiguracionEmpresaSerializer(configuracion, data=request.data, partial=True)
            entrada.is_valid(raise_exception=True)
            anteriores = {
                campo: getattr(configuracion, campo)
                for campo, valor in entrada.validated_data.items()
                if getattr(configuracion, campo) != valor
            }
            if anteriores:
                entrada.save()
                registrar(
                    usuario=request.user,
                    entidad=Entidad.EMPRESA,
                    entidad_id=request.user.empresa_id,
                    accion="EDITAR_CONFIGURACION",
                    datos_previos=anteriores,
                )
        return Response(ConfiguracionEmpresaSerializer(configuracion).data)
