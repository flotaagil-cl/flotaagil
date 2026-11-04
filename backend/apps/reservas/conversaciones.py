"""HU-30: bandeja de conversaciones de WhatsApp por pasajero, con su reserva vinculada.

Dentro de las 24 h desde el último mensaje del pasajero se responde con texto libre (regla de WhatsApp). Fuera
de ella solo caben plantillas aprobadas, pendientes de PR-11, así que el envío se rechaza.

El mensaje se registra antes de enviarse, con quien lo escribió, y el worker lo envía: un fallo queda a la
vista como FAILED en vez de perderse.
"""

from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, Max, OuterRef, Q, Subquery
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException
from rest_framework.response import Response

from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol

from . import tareas
from .models import (
    DireccionMensaje,
    EstadoEntrega,
    EstadoViaje,
    MensajeWhatsapp,
    Pasajero,
    TipoMensaje,
    Viaje,
)

VENTANA = timedelta(hours=24)
MENSAJES_EN_EL_HILO = 200


class FueraDeVentana(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "fuera_de_ventana"
    default_detail = "Fuera de la ventana de 24 h: solo plantillas aprobadas (pendiente PR-11)."


class ReservaVinculadaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado = serializers.ChoiceField(choices=EstadoViaje.choices)


class ConversacionSerializer(serializers.Serializer):
    id = serializers.IntegerField(help_text="El pasajero")
    nombre = serializers.CharField()
    telefono = serializers.CharField()
    ultimo_mensaje = serializers.CharField()
    ultima_direccion = serializers.ChoiceField(choices=DireccionMensaje.choices)
    ultimo_en = serializers.DateTimeField()
    ventana_hasta = serializers.DateTimeField(
        allow_null=True, help_text="Hasta cuándo admite texto libre; NULL si el pasajero nunca escribió"
    )
    dentro_ventana = serializers.BooleanField()
    reserva = ReservaVinculadaSerializer(allow_null=True, help_text="La más reciente del pasajero")


class MensajeSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.nombre", allow_null=True, default=None)

    class Meta:
        model = MensajeWhatsapp
        fields = ["id", "direccion", "tipo", "cuerpo", "estado_entrega", "usuario", "viaje", "creado_en"]
        read_only_fields = fields


class ConversacionDetalleSerializer(ConversacionSerializer):
    mensajes = MensajeSerializer(many=True, help_text=f"Los últimos {MENSAJES_EN_EL_HILO}, en orden")


class MensajeNuevoSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=1024)

    def validate_texto(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Escribe el mensaje.")
        return valor


def _ventana_hasta(pasajero) -> object:
    return pasajero.ultima_entrada + VENTANA if pasajero.ultima_entrada else None


def _datos(pasajero) -> dict:
    hasta = _ventana_hasta(pasajero)
    return {
        "id": pasajero.pk,
        "nombre": pasajero.nombre,
        "telefono": pasajero.telefono,
        "ultimo_mensaje": pasajero.ultimo_mensaje,
        "ultima_direccion": pasajero.ultima_direccion,
        "ultimo_en": pasajero.ultimo_en,
        "ventana_hasta": hasta,
        "dentro_ventana": hasta is not None and hasta > timezone.now(),
        "reserva": (
            {"id": pasajero.reserva_id, "estado": pasajero.reserva_estado} if pasajero.reserva_id else None
        ),
    }


def registrar_y_enviar(pasajero, texto: str, *, usuario, viaje_id) -> MensajeWhatsapp:
    with transaction.atomic():
        mensaje = MensajeWhatsapp.objects.create(
            pasajero=pasajero,
            viaje_id=viaje_id,
            direccion=DireccionMensaje.SALIENTE,
            tipo=TipoMensaje.SESION,
            cuerpo=texto,
            estado_entrega=EstadoEntrega.QUEUED,
            usuario=usuario,
        )
        transaction.on_commit(lambda: tareas.encolar_chat(mensaje.pk), robust=True)
    return mensaje


@extend_schema_view(
    list=extend_schema(
        summary="Bandeja de conversaciones, la más reciente primero",
        tags=["conversaciones"],
        responses=ConversacionSerializer(many=True),
    ),
    retrieve=extend_schema(
        summary="Conversación con un pasajero",
        tags=["conversaciones"],
        responses=ConversacionDetalleSerializer,
    ),
)
class ConversacionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
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
                ultima_entrada=Max(
                    "mensajes__creado_en", filter=Q(mensajes__direccion=DireccionMensaje.ENTRANTE)
                ),
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

    def _detalle(self, pasajero) -> dict:
        ultimos = (
            MensajeWhatsapp.objects.filter(pasajero=pasajero)
            .select_related("usuario")
            .order_by("-creado_en", "-id")[:MENSAJES_EN_EL_HILO]
        )
        return {**_datos(pasajero), "mensajes": MensajeSerializer(reversed(list(ultimos)), many=True).data}

    def retrieve(self, request, pk=None):
        return Response(self._detalle(self.get_object()))

    @extend_schema(
        summary="Responder dentro de la ventana de 24 h",
        tags=["conversaciones"],
        request=MensajeNuevoSerializer,
        responses={
            201: MensajeSerializer,
            409: OpenApiResponse(description="`fuera_de_ventana`: solo plantillas aprobadas (PR-11)"),
        },
        description="Queda registrado con quien lo escribió y lo envía el worker, con reintentos.",
    )
    @action(detail=True, methods=["post"], url_path="mensajes")
    def responder(self, request, pk=None):
        pasajero = self.get_object()
        entrada = MensajeNuevoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        hasta = _ventana_hasta(pasajero)
        if hasta is None or hasta <= timezone.now():
            raise FueraDeVentana()
        mensaje = registrar_y_enviar(
            pasajero, entrada.validated_data["texto"], usuario=request.user, viaje_id=pasajero.reserva_id
        )
        return Response(MensajeSerializer(mensaje).data, status=status.HTTP_201_CREATED)
