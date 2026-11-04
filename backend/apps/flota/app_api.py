"""API de la app del conductor: perfil, consentimiento de ubicación (RN-18) y envío de posiciones GPS.

Solo el rol CONDUCTOR. Cada conductor ve y escribe solo lo suyo (el usuario de la sesión), así que el
aislamiento por empresa (RN-13) queda dado por la cuenta.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.gis.geos import Point
from django.db import transaction
from django.db.models import Exists, OuterRef, Subquery
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_field
from rest_framework import serializers, status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.auditoria.models import Auditoria, Entidad
from apps.comun.permisos import con_roles
from apps.cuentas.models import Rol
from apps.reservas.models import EstadoViaje, HistorialEstado, MetodoPago, Viaje

from .models import Conductor, EstadoConductor, PosicionGps
from .serializers import VehiculoAsociadoSerializer, VehiculoDeclaradoSerializer
from .tiempo_real import avisar_indicadores, notificar_conductor

MAX_POR_LOTE = 100
# Estados del viaje en que la posición del conductor se asocia al viaje.
ESTADOS_CON_VIAJE = (
    EstadoViaje.ACEPTADO,
    EstadoViaje.EN_CAMINO,
    EstadoViaje.EN_ZONA,
    EstadoViaje.PASAJERO_A_BORDO,
)
EN_TURNO = (EstadoConductor.DISPONIBLE, EstadoConductor.EN_VIAJE)


class FueraDeTurno(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "fuera_de_turno"
    default_detail = "La ubicación solo se registra en turno (Disponible o En viaje)."


class SinConsentimiento(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "sin_consentimiento"
    default_detail = "Falta el consentimiento informado para registrar la ubicación."


class LugarEnFilaSerializer(serializers.Serializer):
    posicion = serializers.IntegerField(help_text="Su lugar en la fila: 1 es el siguiente (RN-16)")
    total = serializers.IntegerField()
    zona = serializers.CharField()
    ingreso_en = serializers.DateTimeField()


class PerfilConductorSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    vehiculo_activo = VehiculoDeclaradoSerializer(allow_null=True, read_only=True)
    vehiculos = serializers.SerializerMethodField()
    fila = serializers.SerializerMethodField()

    class Meta:
        model = Conductor
        fields = ["id", "nombre", "estado", "vehiculo_activo", "consentimiento_gps_en", "vehiculos", "fila"]
        read_only_fields = fields

    @staticmethod
    @extend_schema_field(LugarEnFilaSerializer(allow_null=True))
    def get_fila(conductor):
        from apps.aeropuerto.fila import estado_de

        return estado_de(conductor)

    @staticmethod
    @extend_schema_field(VehiculoAsociadoSerializer(many=True))
    def get_vehiculos(conductor):
        activos = [a for a in conductor.asociaciones.all() if a.vehiculo.activo]
        return VehiculoAsociadoSerializer(sorted(activos, key=lambda a: a.vehiculo.patente), many=True).data


class PosicionSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    precision_m = serializers.FloatField(min_value=0, required=False, allow_null=True)
    registrada_en = serializers.DateTimeField()


class LotePosicionesSerializer(serializers.Serializer):
    posiciones = PosicionSerializer(many=True, allow_empty=False, max_length=MAX_POR_LOTE)


class ResultadoLoteSerializer(serializers.Serializer):
    recibidas = serializers.IntegerField(help_text="Guardadas ahora")
    repetidas = serializers.IntegerField(help_text="Ya estaban (reenvío del mismo lote)")
    descartadas = serializers.IntegerField(
        help_text="Precisión > 500 m, del futuro o más antiguas que la retención: no se guardan"
    )


def _conductor(request) -> Conductor:
    return (
        Conductor.objects.select_related("usuario", "vehiculo_activo")
        .prefetch_related("asociaciones__vehiculo")
        .get(usuario=request.user)
    )


class _VistaApp(APIView):
    permission_classes = [con_roles(Rol.CONDUCTOR)]


class PerfilView(_VistaApp):
    @extend_schema(
        tags=["app"], summary="Perfil del conductor de la sesión", responses=PerfilConductorSerializer
    )
    def get(self, request):
        return Response(PerfilConductorSerializer(_conductor(request)).data)


class ConsentimientoView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Aceptar el tratamiento de la ubicación (RN-18)",
        request=None,
        responses=PerfilConductorSerializer,
        description="Guarda la fecha de aceptación. Si ya estaba aceptado, la conserva.",
    )
    def post(self, request):
        conductor = _conductor(request)
        if conductor.consentimiento_gps_en is None:
            conductor.consentimiento_gps_en = timezone.now()
            conductor.save(update_fields=["consentimiento_gps_en"])
        return Response(PerfilConductorSerializer(conductor).data)


class PosicionesView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Enviar un lote de posiciones GPS",
        request=LotePosicionesSerializer,
        responses={
            201: ResultadoLoteSerializer,
            409: OpenApiResponse(description="`fuera_de_turno` o `sin_consentimiento` (RN-18)."),
        },
        description=f"Hasta {MAX_POR_LOTE} posiciones por lote. Idempotente: reenviar el mismo lote no "
        "duplica "
        "(única por conductor e instante). Se asocian al viaje en curso del conductor, si hay uno.",
    )
    def post(self, request):
        entrada = LotePosicionesSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        conductor = _conductor(request)
        if conductor.consentimiento_gps_en is None:
            raise SinConsentimiento()
        if conductor.estado not in EN_TURNO:
            raise FueraDeTurno()

        ahora = timezone.now()
        minimo = ahora - timedelta(days=settings.RETENCION_POSICIONES_DIAS)
        maximo = ahora + timedelta(minutes=2)  # tolerancia del reloj del teléfono
        validas, descartadas = [], 0
        for posicion in entrada.validated_data["posiciones"]:
            precision = posicion.get("precision_m")
            if (precision is not None and precision > 500) or not minimo <= posicion[
                "registrada_en"
            ] <= maximo:
                descartadas += 1
                continue
            validas.append(posicion)

        viaje = (
            Viaje.objects.filter(conductor=conductor, estado__in=ESTADOS_CON_VIAJE)
            .order_by("-recogida_en")
            .first()
        )
        nuevas = [
            PosicionGps(
                conductor=conductor,
                viaje=viaje,
                punto=Point(p["lon"], p["lat"], srid=4326),
                precision_m=None if p.get("precision_m") is None else round(p["precision_m"]),
                registrada_en=p["registrada_en"],
            )
            for p in validas
        ]
        with transaction.atomic():
            # En serie por conductor: el conteo de recibidas no se mezcla con otro lote simultáneo.
            list(Conductor.objects.select_for_update().filter(pk=conductor.pk).values_list("pk"))
            antes = PosicionGps.objects.filter(conductor=conductor).count()
            PosicionGps.objects.bulk_create(nuevas, ignore_conflicts=True)
            recibidas = PosicionGps.objects.filter(conductor=conductor).count() - antes
            if recibidas:
                # HU-02: el mapa recibe la posición más reciente del lote.
                notificar_conductor(conductor)
                # HU-16: EN_ZONA automático por geocerca (import aquí: reservas depende de flota).
                from apps.reservas.ejecucion import marcar_en_zona

                marcar_en_zona(conductor, validas)
                # HU-29: ingreso a la fila del aeropuerto.
                from apps.aeropuerto.fila import registrar_posiciones

                registrar_posiciones(conductor, validas)
        return Response(
            {"recibidas": recibidas, "repetidas": len(validas) - recibidas, "descartadas": descartadas},
            status=status.HTTP_201_CREATED,
        )


# --- Turno (HU-13) ---


class TurnoConflicto(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_code = "turno_no_permitido"
    default_detail = "No se puede cambiar el estado ahora."


class TurnoSerializer(serializers.Serializer):
    estado = serializers.ChoiceField(choices=[EstadoConductor.DISPONIBLE, EstadoConductor.NO_DISPONIBLE])
    vehiculo = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Obligatorio para quedar Disponible con más de un vehículo activo (RN-05).",
    )


def _conflicto(codigo: str, mensaje: str) -> TurnoConflicto:
    return TurnoConflicto(mensaje, code=codigo)


class TurnoView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Empezar o terminar el turno (Disponible / No disponible)",
        request=TurnoSerializer,
        responses={
            200: PerfilConductorSerializer,
            409: OpenApiResponse(
                description="`en_viaje` (RN-03), `sin_consentimiento` (RN-18), `licencia_vencida`, "
                "`sin_vehiculo`, `elegir_vehiculo` (RN-05), `vehiculo_no_disponible` o `vehiculo_ocupado`."
            ),
        },
        description=(
            "Disponible exige consentimiento de ubicación, licencia vigente y declarar el vehículo "
            "del turno: si tiene uno activo se usa ese; si tiene más, hay que elegirlo. Un vehículo "
            "no puede estar declarado por dos conductores en turno. No disponible borra el vehículo "
            "declarado. Desde En viaje no se cambia aquí."
        ),
    )
    def post(self, request):
        entrada = TurnoSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        with transaction.atomic():
            conductor = (
                Conductor.objects.select_for_update(of=("self",))
                .select_related("usuario")
                .get(usuario=request.user)
            )
            if conductor.estado == EstadoConductor.EN_VIAJE:
                raise _conflicto("en_viaje", "Estás en un viaje: el estado cambia al terminarlo (RN-03).")
            previo = conductor.estado
            if entrada.validated_data["estado"] == EstadoConductor.NO_DISPONIBLE:
                conductor.estado, conductor.vehiculo_activo = EstadoConductor.NO_DISPONIBLE, None
                if previo != EstadoConductor.NO_DISPONIBLE:
                    conductor.turno_fin = timezone.now()  # DC-26
            else:
                conductor.vehiculo_activo = self._vehiculo_del_turno(
                    conductor, entrada.validated_data.get("vehiculo")
                )
                conductor.estado = EstadoConductor.DISPONIBLE
                if previo == EstadoConductor.NO_DISPONIBLE:
                    conductor.turno_inicio, conductor.turno_fin = timezone.now(), None  # DC-26
            conductor.save(update_fields=["estado", "vehiculo_activo", "turno_inicio", "turno_fin"])
            notificar_conductor(conductor)
            avisar_indicadores(request.user.empresa_id)  # HU-01
            if conductor.estado == EstadoConductor.NO_DISPONIBLE:
                from apps.aeropuerto.fila import salir
                from apps.aeropuerto.models import MotivoSalidaFila

                salir(conductor, MotivoSalidaFila.NO_DISPONIBLE)  # HU-29
        return Response(PerfilConductorSerializer(_conductor(request)).data)

    @staticmethod
    def _vehiculo_del_turno(conductor: Conductor, elegido: int | None):
        if conductor.consentimiento_gps_en is None:
            raise _conflicto(
                "sin_consentimiento", "Acepta el uso de tu ubicación antes de empezar el turno (RN-18)."
            )
        if conductor.licencia_vence <= timezone.localdate():
            raise _conflicto(
                "licencia_vencida", "Tu licencia está vencida. Habla con el administrador de tu empresa."
            )
        activos = [a.vehiculo for a in conductor.asociaciones.select_related("vehiculo") if a.vehiculo.activo]
        if not activos:
            raise _conflicto(
                "sin_vehiculo", "No tienes vehículos activos asociados. Habla con el administrador."
            )
        if elegido is None:
            if len(activos) > 1:
                raise _conflicto("elegir_vehiculo", "Elige el vehículo que usarás en este turno (RN-05).")
            vehiculo = activos[0]
        else:
            vehiculo = next((v for v in activos if v.pk == elegido), None)
            if vehiculo is None:
                raise _conflicto(
                    "vehiculo_no_disponible", "Ese vehículo no está asociado a ti o está inactivo."
                )
        ocupado = (
            Conductor.objects.filter(vehiculo_activo=vehiculo, estado__in=EN_TURNO)
            .exclude(pk=conductor.pk)
            .select_related("usuario")
            .first()
        )
        if ocupado:
            raise _conflicto(
                "vehiculo_ocupado", f"El vehículo {vehiculo.patente} ya está en turno con otro conductor."
            )
        return vehiculo


# --- Mi turno (HU-18) ---


class ViajeDelTurnoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    finalizado_en = serializers.DateTimeField()
    origen = serializers.CharField()
    destino = serializers.CharField()
    monto = serializers.IntegerField()
    metodo = serializers.ChoiceField(choices=MetodoPago.choices)
    cerrado_por_central = serializers.BooleanField(help_text="Cierre forzado desde el panel (HU-05)")


class TotalPorMetodoSerializer(serializers.Serializer):
    metodo = serializers.ChoiceField(choices=MetodoPago.choices)
    viajes = serializers.IntegerField()
    monto = serializers.IntegerField()


class MiTurnoSerializer(serializers.Serializer):
    en_turno = serializers.BooleanField()
    inicio = serializers.DateTimeField(allow_null=True, help_text="NULL si aún no hay un turno registrado")
    fin = serializers.DateTimeField(allow_null=True, help_text="NULL mientras el turno sigue en curso")
    viajes = ViajeDelTurnoSerializer(many=True)
    totales = TotalPorMetodoSerializer(many=True, help_text="Para rendir caja, solo los métodos usados")
    total = serializers.IntegerField()


def _viajes_del_turno(conductor: Conductor) -> list[Viaje]:
    """Viajes finalizados entre el inicio y el fin del turno (DC-26), del más antiguo al más nuevo."""
    if conductor.turno_inicio is None:
        return []
    finalizado_en = HistorialEstado.objects.filter(
        viaje=OuterRef("pk"), estado_nuevo=EstadoViaje.FINALIZADO
    ).values("creado_en")[:1]
    viajes = (
        Viaje.objects.filter(conductor=conductor, estado=EstadoViaje.FINALIZADO, pago__isnull=False)
        .select_related("pago")
        .annotate(
            finalizado_en=Subquery(finalizado_en),
            cerrado_por_central=Exists(
                Auditoria.objects.filter(
                    entidad=Entidad.VIAJE, entidad_id=OuterRef("pk"), accion="CIERRE_FORZADO"
                )
            ),
        )
        .filter(finalizado_en__gte=conductor.turno_inicio)
        .order_by("finalizado_en")
    )
    if conductor.turno_fin is not None:
        viajes = viajes.filter(finalizado_en__lte=conductor.turno_fin)
    return list(viajes)


class MiTurnoView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Viajes completados en el turno",
        responses=MiTurnoSerializer,
        description=(
            "Los viajes FINALIZADOS del turno actual o, fuera de turno, del último. "
            "Incluye los cerrados por la central, marcados, y los totales por método de pago."
        ),
    )
    def get(self, request):
        conductor = Conductor.objects.get(usuario=request.user)
        viajes = _viajes_del_turno(conductor)
        totales = {
            metodo: {
                "metodo": metodo,
                "viajes": sum(1 for v in viajes if v.pago.metodo == metodo),
                "monto": sum(v.pago.monto for v in viajes if v.pago.metodo == metodo),
            }
            for metodo in MetodoPago.values
        }
        return Response(
            {
                "en_turno": conductor.estado in EN_TURNO,
                "inicio": conductor.turno_inicio,
                "fin": conductor.turno_fin,
                "viajes": [
                    {
                        "id": v.pk,
                        "finalizado_en": v.finalizado_en,
                        "origen": v.origen_dir,
                        "destino": v.destino_dir,
                        "monto": v.pago.monto,
                        "metodo": v.pago.metodo,
                        "cerrado_por_central": v.cerrado_por_central,
                    }
                    for v in viajes
                ],
                "totales": [t for t in totales.values() if t["viajes"]],
                "total": sum(v.pago.monto for v in viajes),
            }
        )


# --- Viaje activo (HU-17) ---


class PuntoSerializer(serializers.Serializer):
    direccion = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class ViajeActivoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    estado = serializers.CharField()
    pasajero = serializers.CharField(help_text="Nombre del pasajero")
    recogida_en = serializers.DateTimeField()
    origen = PuntoSerializer()
    destino = PuntoSerializer()
    vuelo = serializers.CharField(allow_null=True, help_text="Número de vuelo, si es desde el aeropuerto")
    tarifa = serializers.IntegerField(allow_null=True, help_text="Tarifa acordada (CLP), si la hay")
    convenio = serializers.BooleanField(help_text="El viaje pertenece a un convenio")
    hacia = PuntoSerializer(
        help_text="A dónde navegar ahora: el origen hasta subir el pasajero, luego el destino"
    )


class RespuestaViajeActivoSerializer(serializers.Serializer):
    viaje = ViajeActivoSerializer(allow_null=True)


def _punto(direccion, punto) -> dict:
    return {"direccion": direccion, "lat": punto.y, "lon": punto.x}


class ViajeActivoView(_VistaApp):
    @extend_schema(
        tags=["app"],
        summary="Viaje en curso del conductor",
        responses=RespuestaViajeActivoSerializer,
        description=(
            "El viaje aceptado y no terminado (ACEPTADO, EN_CAMINO, EN_ZONA o PASAJERO_A_BORDO), "
            "con las coordenadas para navegar. `viaje` es null si no hay uno."
        ),
    )
    def get(self, request):
        viaje = (
            Viaje.objects.select_related("pasajero", "vuelo")
            .filter(conductor__usuario=request.user, estado__in=ESTADOS_CON_VIAJE)
            .order_by("recogida_en")
            .first()
        )
        if viaje is None:
            return Response({"viaje": None})
        origen = _punto(viaje.origen_dir, viaje.origen_geo)
        destino = _punto(viaje.destino_dir, viaje.destino_geo)
        return Response(
            {
                "viaje": {
                    "id": viaje.pk,
                    "estado": viaje.estado,
                    "pasajero": viaje.pasajero.nombre,
                    "recogida_en": viaje.recogida_en,
                    "origen": origen,
                    "destino": destino,
                    "vuelo": getattr(getattr(viaje, "vuelo", None), "numero", None),
                    "tarifa": viaje.tarifa,
                    "convenio": viaje.convenio_id is not None,
                    "hacia": destino if viaje.estado == EstadoViaje.PASAJERO_A_BORDO else origen,
                }
            }
        )
