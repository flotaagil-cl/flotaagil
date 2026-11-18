"""HU-30 con CC-19 (HU-67): historial de WhatsApp en solo lectura, por pasajero, con su reserva vinculada.

El canal se retiró: ya no se escribe ni se recibe nada por WhatsApp y el chat interno lo reemplaza. Lo que se
conversó queda visible para el equipo («Historial WhatsApp (canal retirado)») hasta que vence su retención
de 12 meses (RN-15, HU-68).
"""

from django.db.models import Exists, Max, OuterRef, Subquery
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import mixins, serializers, viewsets
from rest_framework.response import Response

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol

from .models import DireccionMensaje, EstadoViaje, MensajeWhatsapp, Pasajero, Viaje

MENSAJES_EN_EL_HILO = 200


class ReservaVinculadaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado = serializers.ChoiceField(choices=EstadoViaje.choices)


class ConversacionSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="El pasajero")
    nombre = serializers.CharField()
    telefono = serializers.CharField(allow_null=True)
    ultimo_mensaje = serializers.CharField()
    ultima_direccion = serializers.ChoiceField(choices=DireccionMensaje.choices)
    ultimo_en = serializers.DateTimeField()
    reserva = ReservaVinculadaSerializer(allow_null=True, help_text="La más reciente del pasajero")


class MensajeSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.nombre", allow_null=True, default=None)

    class Meta:
        model = MensajeWhatsapp
        fields = ["id", "direccion", "tipo", "cuerpo", "estado_entrega", "usuario", "viaje", "creado_en"]
        read_only_fields = fields


class ConversacionDetalleSerializer(ConversacionSerializer):
    mensajes = MensajeSerializer(many=True, help_text=f"Los últimos {MENSAJES_EN_EL_HILO}, en orden")


def _datos(pasajero) -> dict:
    return {
        "id": pasajero.pk,
        "nombre": pasajero.nombre,
        "telefono": pasajero.telefono,
        "ultimo_mensaje": pasajero.ultimo_mensaje,
        "ultima_direccion": pasajero.ultima_direccion,
        "ultimo_en": pasajero.ultimo_en,
        "reserva": (
            {"id": pasajero.reserva_id, "estado": pasajero.reserva_estado} if pasajero.reserva_id else None
        ),
    }


@extend_schema_view(
    list=extend_schema(
        summary="Historial de WhatsApp (canal retirado), la conversación más reciente primero",
        tags=["conversaciones"],
        responses=ConversacionSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Historial de WhatsApp con un pasajero (solo lectura)",
        tags=["conversaciones"],
        responses=ConversacionDetalleSerializer,
    ),
)
class ConversacionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [con_roles(Rol.ADMINISTRADOR, Rol.DESPACHADOR)]
    filter_backends: list = []
    serializer_class = ConversacionSerializer
    queryset = Pasajero.objects.none()  # El real depende de la empresa del usuario (RN-13).

    def get_queryset(self):
        ultimo = MensajeWhatsapp.objects.filter(pasajero=OuterRef("pk")).order_by("-creado_en", "-id")
        reserva = Viaje.objects.filter(pasajero=OuterRef("pk")).order_by("-id")
        return (
            Pasajero.objects.filter(Exists(MensajeWhatsapp.objects.filter(pasajero=OuterRef("pk"))))
            .annotate(
                ultimo_en=Max("mensajes__creado_en"),
                ultimo_mensaje=Subquery(ultimo.values("cuerpo")[:1]),
                ultima_direccion=Subquery(ultimo.values("direccion")[:1]),
                reserva_id=Subquery(reserva.values("pk")[:1]),
                reserva_estado=Subquery(reserva.values("estado")[:1]),
            )
            .filter(empresa=self.request.user.empresa_id)
            .order_by("-ultimo_en", "-id")
        )

    def list(self, request):
        pagina = self.paginate_queryset(self.get_queryset())
        return self.get_paginated_response(
            ConversacionSerializer([_datos(p) for p in pagina], many=True).data
        )

    def retrieve(self, request, pk=None):
        pasajero = self.get_object()
        ultimos = (
            MensajeWhatsapp.objects.filter(pasajero=pasajero)
            .select_related("usuario")
            .order_by("-creado_en", "-id")[:MENSAJES_EN_EL_HILO]
        )
        return Response(
            {**_datos(pasajero), "mensajes": MensajeSerializer(reversed(list(ultimos)), many=True).data}
        )
