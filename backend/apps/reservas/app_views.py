"""Respuesta del conductor a un viaje asignado, desde la app (HU-15)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol

from . import asignacion as servicio
from . import ejecucion
from .models import MONTO_MAXIMO, MetodoPago


class RespuestaAsignacionSerializer(serializers.Serializer):
    asignacion = serializers.IntegerField()
    viaje = serializers.IntegerField()
    resultado = serializers.CharField()
    estado_viaje = serializers.CharField()


CONFLICTO = OpenApiResponse(
    description="`asignacion_no_permitida`: ya respondida o pasaron los 60 s (RN-04)."
)


class _Responder(APIView):
    permission_classes = [con_roles(Rol.CONDUCTOR)]
    aceptar = True

    def post(self, request, pk):
        asignacion = servicio.responder(pk, usuario=request.user, aceptar=self.aceptar)
        asignacion.viaje.refresh_from_db()
        return Response(
            {
                "asignacion": asignacion.pk,
                "viaje": asignacion.viaje_id,
                "resultado": asignacion.resultado,
                "estado_viaje": asignacion.viaje.estado,
            }
        )


class AceptarView(_Responder):
    aceptar = True

    @extend_schema(
        tags=["app"],
        summary="Aceptar el viaje asignado",
        request=None,
        responses={200: RespuestaAsignacionSerializer, 409: CONFLICTO},
        description="Dentro de los 60 s: el viaje queda ACEPTADO y el conductor En viaje.",
    )
    def post(self, request, pk):
        return super().post(request, pk)


class RechazarView(_Responder):
    aceptar = False

    @extend_schema(
        tags=["app"],
        summary="Rechazar el viaje asignado",
        request=None,
        responses={200: RespuestaAsignacionSerializer, 409: CONFLICTO},
        description="La reserva vuelve a SOLICITADO para reasignarla (RN-04).",
    )
    def post(self, request, pk):
        return super().post(request, pk)


# --- Ejecución del viaje (HU-16) ---


class EstadoViajeSerializer(serializers.Serializer):
    viaje = serializers.IntegerField()
    estado = serializers.CharField()


class FinalizarSerializer(serializers.Serializer):
    metodo = serializers.ChoiceField(choices=MetodoPago.choices)
    monto = serializers.IntegerField(min_value=0, max_value=MONTO_MAXIMO, help_text="Monto cobrado en CLP")


ESTADO_NO_PERMITIDO = OpenApiResponse(
    description="`estado_no_permitido`: el viaje no está en el estado previo."
)


def _respuesta(viaje):
    return Response({"viaje": viaje.pk, "estado": viaje.estado})


class _VistaViaje(APIView):
    permission_classes = [con_roles(Rol.CONDUCTOR)]


class EnCaminoView(_VistaViaje):
    @extend_schema(
        tags=["app"],
        summary="Salir hacia el punto de recogida (EN_CAMINO)",
        request=None,
        responses={200: EstadoViajeSerializer, 409: ESTADO_NO_PERMITIDO},
    )
    def post(self, request, pk):
        return _respuesta(ejecucion.en_camino(pk, usuario=request.user))


class ABordoView(_VistaViaje):
    @extend_schema(
        tags=["app"],
        summary="Indicar que el pasajero subió (PASAJERO_A_BORDO)",
        request=None,
        responses={200: EstadoViajeSerializer, 409: ESTADO_NO_PERMITIDO},
        description="Desde EN_ZONA. Desde EN_CAMINO (la geocerca no lo marcó), registra antes EN_ZONA con "
        "actor CONDUCTOR (DC-17).",
    )
    def post(self, request, pk):
        return _respuesta(ejecucion.pasajero_a_bordo(pk, usuario=request.user))


class FinalizarView(_VistaViaje):
    @extend_schema(
        tags=["app"],
        summary="Finalizar el viaje con el pago (RN-10)",
        request=FinalizarSerializer,
        responses={200: EstadoViajeSerializer, 409: ESTADO_NO_PERMITIDO},
        description="Método y monto obligatorios. El conductor queda Disponible.",
    )
    def post(self, request, pk):
        entrada = FinalizarSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        return _respuesta(ejecucion.finalizar(pk, usuario=request.user, **entrada.validated_data))
