"""Respuesta del conductor a un viaje asignado, desde la app (HU-15)."""

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol

from . import asignacion as servicio


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
