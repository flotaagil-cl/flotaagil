"""HU-35: API de la cuenta del pasajero (`/api/mi-cuenta/`). Solo rol PASAJERO, con la cuenta confirmada; ve
solo las reservas de su teléfono en su empresa (RN-13)."""

from urllib.parse import urlsplit

from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_field
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.comun.permisos import ConModuloCuentas, con_roles
from apps.cuentas.models import Rol
from apps.integraciones import push
from apps.portal.serializers import (
    PersonaPasajeroSerializer,
    ReservaConPaseMixin,
    SolicitudRespuestaSerializer,
    SolicitudSerializer,
)

from . import cuentas_pasajero as cuentas
from .models import EstadoViaje, SuscripcionPush, Viaje
from .serializers import HistorialSerializer, PasajeroEntradaSerializer

SOLO_PASAJERO = [con_roles(Rol.PASAJERO), ConModuloCuentas]  # DC-51


class CentralSerializer(serializers.Serializer):
    """HU-66 (DC-62): botones de emergencia; null si la empresa no lo configuró. HU-49 (DC-80): sin WhatsApp,
    el del teléfono de la central."""

    telefono = serializers.CharField(allow_null=True)
    whatsapp = serializers.CharField(allow_null=True)


class MiCuentaSerializer(serializers.Serializer):
    nombre = serializers.CharField()
    email = serializers.EmailField(source="usuario.email")
    telefono = serializers.CharField()
    empresa = serializers.CharField(source="empresa.razon_social")
    empresa_slug = serializers.CharField(source="empresa.slug")
    # HU-45: datos de «Mi perfil».
    pasajero_desde = serializers.DateTimeField(source="confirmada_en")
    acepta_avisos_correo = serializers.BooleanField(help_text="DC-62: avisos del viaje por correo.")
    central = serializers.SerializerMethodField(help_text="HU-66: números de emergencia de la central.")
    password_cambiada_en = serializers.SerializerMethodField(
        help_text="Último cambio o recuperación de la contraseña registrado en la auditoría, o null."
    )

    @extend_schema_field(CentralSerializer)
    def get_central(self, cuenta):
        return cuenta.empresa.configuracion.numeros_central()

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_password_cambiada_en(self, cuenta):
        from apps.auditoria.models import Auditoria, Entidad

        ultima = (
            Auditoria.objects.filter(
                entidad=Entidad.USUARIO,
                entidad_id=cuenta.usuario_id,
                accion__in=["CAMBIAR_PASSWORD", "RECUPERAR_PASSWORD"],
            )
            .order_by("-creado_en")
            .values_list("creado_en", flat=True)
            .first()
        )
        return ultima


class PerfilEntradaSerializer(serializers.Serializer):
    """HU-45: el correo es el usuario de ingreso y no se cambia aquí."""

    nombre = serializers.CharField(max_length=80, required=False)
    telefono = serializers.CharField(
        max_length=24, required=False, help_text="Teléfono de contacto en formato E.164 (sin verificar)."
    )
    acepta_avisos_correo = serializers.BooleanField(
        required=False, help_text="DC-62: avisos del viaje por correo."
    )

    def validate_nombre(self, valor):
        return PasajeroEntradaSerializer().validate_nombre(valor)

    def validate_telefono(self, valor):
        return PasajeroEntradaSerializer().validate_telefono(valor)


class MiReservaSerializer(serializers.ModelSerializer):
    estado_texto = serializers.CharField(source="get_estado_display")
    cancelable = serializers.SerializerMethodField()
    historial = HistorialSerializer(many=True, read_only=True)

    class Meta:
        model = Viaje
        fields = [
            "id",
            "estado",
            "estado_texto",
            "canal",
            "sentido",
            "origen_dir",
            "destino_dir",
            "recogida_en",
            "cancelable",
            "historial",
        ]

    def get_cancelable(self, viaje) -> bool:
        return viaje.estado in cuentas.CANCELABLES


class SolicitudCuentaSerializer(ReservaConPaseMixin, SolicitudSerializer):
    """Los datos de quien pide salen de la cuenta: nombre y teléfono se ignoran si vienen. DC-44: el pedido no
    acepta nada (la cuenta ya aceptó una vez); las aceptaciones se ignoran si vienen.

    CC-26 (HU-76, DC-82): como en CC-23 y CC-25, para sí o para otra persona (`para`, `pasajero_*`), con
    `acompanantes` en el mismo vehículo o en vehículos separados (`vehiculos`), sin cargo. Por los terceros,
    `declara_informados`. Sin acompañantes, `pasajeros` vale 1."""

    pase = None
    pide_cargo = False
    acompanantes = PersonaPasajeroSerializer(many=True, required=False, default=list)
    nombre = serializers.CharField(max_length=80, required=False)
    telefono = serializers.CharField(max_length=24, required=False)
    acepta_privacidad = serializers.BooleanField(required=False)
    acepta_whatsapp = serializers.BooleanField(required=False)

    def validate_acepta_privacidad(self, valor):
        return valor

    def validate_acepta_whatsapp(self, valor):
        return valor

    def validate(self, datos):
        return self.validar_pase(super().validate(datos))


class PedidoRecibidoSerializer(SolicitudRespuestaSerializer):
    """HU-42: con cuenta, la respuesta trae el número de la reserva (el pasajero solo ve las suyas)."""

    id = serializers.IntegerField(help_text="Número de la reserva, para «Ver mi viaje».")
    viajes = serializers.IntegerField(
        help_text="CC-26: viajes creados (uno por persona en vehículos separados); `id` es el primero."
    )


class AceptarPrivacidadSerializer(serializers.Serializer):
    acepta = serializers.BooleanField()

    def validate_acepta(self, valor):
        if not valor:
            raise serializers.ValidationError("Para seguir debes aceptar el aviso de privacidad.")
        return valor


class PrivacidadAceptadaSerializer(serializers.Serializer):
    aceptada_en = serializers.DateTimeField()
    version = serializers.CharField()


class MiPrivacidadView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Aceptar el aviso de privacidad vigente",
        request=AceptarPrivacidadSerializer,
        responses={200: PrivacidadAceptadaSerializer},
        description="DC-44: para las cuentas que no lo aceptaron o cuando cambia la versión del aviso.",
    )
    def post(self, request):
        AceptarPrivacidadSerializer(data=request.data).is_valid(raise_exception=True)
        cuenta = cuentas.aceptar_privacidad(request.user)
        datos = {"aceptada_en": cuenta.privacidad_aceptada_en, "version": cuenta.privacidad_version}
        return Response(PrivacidadAceptadaSerializer(datos).data)


class MiCuentaView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Mi cuenta",
        responses={200: MiCuentaSerializer, 409: OpenApiResponse(description="`cuenta_sin_confirmar`")},
    )
    def get(self, request):
        return Response(MiCuentaSerializer(cuentas.cuenta_activa(request.user)).data)

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Editar mi perfil",
        request=PerfilEntradaSerializer,
        responses={
            200: MiCuentaSerializer,
            409: OpenApiResponse(description="`telefono_en_uso` o `cuenta_sin_confirmar`"),
        },
        description="El nombre y el teléfono cambian al tiro, sin verificación (HU-64, DC-61). Un teléfono "
        "que ya es de otra cuenta o de otro pasajero de la empresa responde 409 (DC-65).",
    )
    def patch(self, request):
        entrada = PerfilEntradaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        cuenta = cuentas.actualizar_perfil(request.user, entrada.validated_data)
        cuenta.refresh_from_db()
        return Response(MiCuentaSerializer(cuenta).data)

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Eliminar mi cuenta",
        responses={204: None, 409: OpenApiResponse(description="`viaje_activo`")},
        description="Anonimiza la cuenta (HU-45, DC-50): usuario inactivo y sin clave, pasajero «Pasajero "
        "eliminado» sin teléfono y mensajes sin contenido. Viajes, pagos, historial y auditoría se "
        "conservan.",
    )
    def delete(self, request):
        cuentas.eliminar(request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# HU-43: el pasajero ve a su conductor, el vehículo y la patente desde que el conductor acepta el viaje.
CON_CONDUCTOR_VISIBLE = frozenset(
    {
        EstadoViaje.ACEPTADO,
        EstadoViaje.EN_CAMINO,
        EstadoViaje.EN_ZONA,
        EstadoViaje.PASAJERO_A_BORDO,
        EstadoViaje.FINALIZADO,
    }
)


class PuntoDeMiViajeSerializer(serializers.Serializer):
    lat = serializers.FloatField()
    lng = serializers.FloatField()


class PasoSerializer(serializers.Serializer):
    """Historial para el pasajero: solo el estado y la hora (sin quién lo cambió)."""

    estado = serializers.CharField(source="estado_nuevo")
    creado_en = serializers.DateTimeField()


class ConductorDeMiViajeSerializer(serializers.Serializer):
    nombre = serializers.CharField(source="usuario.nombre")


class VehiculoDeMiViajeSerializer(serializers.Serializer):
    marca_modelo = serializers.CharField()
    patente = serializers.CharField()


class VueloDeMiViajeSerializer(serializers.Serializer):
    numero = serializers.CharField()
    hora_programada = serializers.DateTimeField()
    hora_estimada = serializers.DateTimeField(allow_null=True)
    estado_vuelo = serializers.CharField()


class TuViajeSerializer(serializers.ModelSerializer):
    """HU-43: el viaje del pasajero con su cuenta (solo los suyos)."""

    estado_texto = serializers.CharField(source="get_estado_display")
    cancelable = serializers.SerializerMethodField()
    origen = serializers.SerializerMethodField()
    destino = serializers.SerializerMethodField()
    conductor = serializers.SerializerMethodField()
    vehiculo = serializers.SerializerMethodField()
    vuelo = serializers.SerializerMethodField()
    pasos = PasoSerializer(source="historial", many=True, read_only=True)

    class Meta:
        model = Viaje
        fields = [
            "id",
            "estado",
            "estado_texto",
            "sentido",
            "origen_dir",
            "destino_dir",
            "origen",
            "destino",
            "recogida_en",
            "pasajeros",
            "maletas",
            "vuelo_salida_en",
            "vuelo_salida_tipo",
            "vuelo_salida_numero",
            "creado_en",
            "cancelable",
            "conductor",
            "vehiculo",
            "vuelo",
            "pasos",
        ]

    def get_cancelable(self, viaje) -> bool:
        return viaje.estado in cuentas.CANCELABLES

    @extend_schema_field(PuntoDeMiViajeSerializer)
    def get_origen(self, viaje):
        return {"lat": viaje.origen_geo.y, "lng": viaje.origen_geo.x}

    @extend_schema_field(PuntoDeMiViajeSerializer)
    def get_destino(self, viaje):
        return {"lat": viaje.destino_geo.y, "lng": viaje.destino_geo.x}

    @extend_schema_field(ConductorDeMiViajeSerializer(allow_null=True))
    def get_conductor(self, viaje):
        if viaje.estado not in CON_CONDUCTOR_VISIBLE or viaje.conductor is None:
            return None
        return ConductorDeMiViajeSerializer(viaje.conductor).data

    @extend_schema_field(VehiculoDeMiViajeSerializer(allow_null=True))
    def get_vehiculo(self, viaje):
        if viaje.estado not in CON_CONDUCTOR_VISIBLE or viaje.vehiculo is None:
            return None
        return VehiculoDeMiViajeSerializer(viaje.vehiculo).data

    @extend_schema_field(VueloDeMiViajeSerializer(allow_null=True))
    def get_vuelo(self, viaje):
        vuelo = getattr(viaje, "vuelo", None)
        return VueloDeMiViajeSerializer(vuelo).data if vuelo else None


class TuViajeView(RetrieveAPIView):
    permission_classes = SOLO_PASAJERO
    serializer_class = TuViajeSerializer

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Tu viaje (HU-43)",
        description="Solo un viaje del pasajero (404 si no es suyo); conductor y patente desde ACEPTADO.",
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Viaje.objects.none()
        return (
            cuentas.reservas_de(cuentas.cuenta_activa(self.request.user))
            .select_related("conductor__usuario", "vehiculo", "vuelo")
            .prefetch_related("historial")
        )


class MisReservasView(ListAPIView):
    permission_classes = SOLO_PASAJERO
    serializer_class = MiReservaSerializer

    @extend_schema(tags=["mi-cuenta"], summary="Mis reservas, incluidas las de invitado, con su historial")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Viaje.objects.none()
        return cuentas.reservas_de(cuentas.cuenta_activa(self.request.user)).prefetch_related(
            "historial__usuario"
        )


class CancelarMiReservaSerializer(serializers.Serializer):
    motivo = serializers.ChoiceField(
        choices=list(cuentas.MOTIVOS_CANCELACION.items()), required=False, help_text="HU-44: motivo elegido."
    )


class CancelarMiReservaView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Cancelar una reserva sin conductor asignado (RN-09)",
        request=CancelarMiReservaSerializer,
        responses={200: MiReservaSerializer, 404: None, 409: OpenApiResponse(description="`con_conductor`")},
    )
    def post(self, request, pk):
        cuenta = cuentas.cuenta_activa(request.user)
        entrada = CancelarMiReservaSerializer(data=request.data or {})
        entrada.is_valid(raise_exception=True)
        viaje = cuentas.cancelar(
            cuenta, pk, usuario=request.user, motivo=entrada.validated_data.get("motivo")
        )
        return Response(
            MiReservaSerializer(Viaje.objects.prefetch_related("historial").get(pk=viaje.pk)).data
        )


class SolicitudMiCuentaView(APIView):
    permission_classes = SOLO_PASAJERO

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Pedir un viaje con mi cuenta",
        request=SolicitudCuentaSerializer,
        responses={
            201: PedidoRecibidoSerializer,
            403: OpenApiResponse(description="`aceptar_privacidad`: falta aceptar el aviso vigente (DC-44)"),
            429: OpenApiResponse(description="`limite_telefono`"),
        },
        description="Queda SOLICITADO sin verificación por WhatsApp; se mantiene el límite por cuenta. "
        "CC-26: para sí o para otra persona, con acompañantes, en el mismo vehículo o un viaje por "
        "persona (mismo `grupo`). Todo o nada.",
    )
    def post(self, request):
        cuenta = cuentas.cuenta_activa(request.user)
        entrada = SolicitudCuentaSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        viajes, respuesta = cuentas.solicitar(cuenta, entrada.validated_data, usuario=request.user)
        datos = {**respuesta, "id": viajes[0].pk}
        return Response(PedidoRecibidoSerializer(datos).data, status=status.HTTP_201_CREATED)


class ClavesPushSerializer(serializers.Serializer):
    p256dh = serializers.CharField(max_length=100)
    auth = serializers.CharField(max_length=40)


class SuscripcionPushSerializer(serializers.Serializer):
    """La suscripción tal como la entrega `PushSubscription.toJSON()` del navegador."""

    endpoint = serializers.URLField(max_length=500)
    keys = ClavesPushSerializer(required=False)

    def validate_endpoint(self, valor):
        """Solo servicios de push conocidos y por https: el backend no llama a cualquier URL (SSRF)."""
        partes = urlsplit(valor)
        host = (partes.hostname or "").lower()
        conocido = any(host == s or host.endswith(f".{s}") for s in settings.WEBPUSH_SERVICIOS)
        if partes.scheme != "https" or not conocido:
            raise serializers.ValidationError("Servicio de push no admitido.", code="push_no_admitido")
        return valor


class ClavePushSerializer(serializers.Serializer):
    clave_publica = serializers.CharField(
        allow_null=True, help_text="VAPID en base64url; null si no hay Web Push."
    )


class PushView(APIView):
    """HU-65 (DC-62): avisos del viaje por Web Push en los navegadores del pasajero que lo aceptan."""

    permission_classes = SOLO_PASAJERO

    @extend_schema(tags=["mi-cuenta"], summary="Clave pública VAPID", responses=ClavePushSerializer)
    def get(self, request):
        clave = settings.WEBPUSH_VAPID_PUBLICA if push.configurado() else None
        return Response({"clave_publica": clave})

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Guardar la suscripción de este navegador",
        request=SuscripcionPushSerializer,
        responses={201: None, 400: OpenApiResponse(description="`push_no_admitido` o datos inválidos")},
    )
    def post(self, request):
        cuentas.cuenta_activa(request.user)
        entrada = SuscripcionPushSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        claves = entrada.validated_data.get("keys")
        if not claves:
            raise serializers.ValidationError({"keys": ["Faltan las claves de la suscripción."]})
        SuscripcionPush.objects.update_or_create(
            endpoint=entrada.validated_data["endpoint"],
            defaults={"usuario": request.user, "p256dh": claves["p256dh"], "auth": claves["auth"]},
        )
        return Response(status=status.HTTP_201_CREATED)

    @extend_schema(
        tags=["mi-cuenta"],
        summary="Quitar la suscripción de este navegador",
        request=SuscripcionPushSerializer,
        responses={204: None},
    )
    def delete(self, request):
        entrada = SuscripcionPushSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        SuscripcionPush.objects.filter(
            usuario=request.user, endpoint=entrada.validated_data["endpoint"]
        ).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
