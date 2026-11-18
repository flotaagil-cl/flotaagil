from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.aeropuerto.models import TipoAlertaVuelo, Vuelo
from apps.auditoria.models import Auditoria, Entidad
from apps.comun.validadores import normalizar_telefono, validar_telefono_e164, validar_vuelo_iata
from apps.convenios.models import Convenio, EstadoConvenio

from . import estados
from .models import MONTO_MAXIMO, Canal, EstadoViaje, HistorialEstado, MetodoPago, Sentido, Viaje


class UbicacionSerializer(serializers.Serializer):
    direccion = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class PasajeroResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    telefono = serializers.CharField(
        allow_null=True, help_text="Null si el pasajero eliminó su cuenta (DC-50)."
    )


class ConductorResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField(source="usuario.nombre")


class VehiculoResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    patente = serializers.CharField()


class ConvenioResumenSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    cliente_nombre = serializers.CharField()


class VueloSerializer(serializers.ModelSerializer):
    # HU-69: calculados con la configuración de la empresa (contexto `configuracion`); no consultan la API.
    internacional = serializers.SerializerMethodField(
        help_text="Según el aeropuerto de origen; null si la API aún no lo informa (DC-69)."
    )
    margen_min = serializers.SerializerMethodField(help_text="Margen de la recogida tras la llegada (RN-17).")
    recogida_sugerida = serializers.SerializerMethodField(
        help_text="Llegada (estimada o programada) + margen (RN-17)."
    )

    class Meta:
        model = Vuelo
        fields = [
            "numero",
            "fecha",
            "hora_programada",
            "hora_estimada",
            "estado_vuelo",
            "ultima_consulta_en",
            "origen_icao",
            "origen_ciudad",
            "origen_aeropuerto",
            "recogida_propuesta",
            "propuesta_en",
            "internacional",
            "margen_min",
            "recogida_sugerida",
        ]
        extra_kwargs = {
            "ultima_consulta_en": {
                "help_text": "Última consulta a la API de vuelos; null = sin verificar (HU-26)."
            }
        }

    def _calculados(self, vuelo) -> dict:
        from apps.aeropuerto.informacion import datos_del_vuelo

        if not hasattr(self, "_cache_calculados"):
            configuracion = self.context.get("configuracion") or vuelo.viaje.empresa.configuracion
            self._cache_calculados = datos_del_vuelo(vuelo, configuracion)
        return self._cache_calculados

    @extend_schema_field(serializers.BooleanField(allow_null=True))
    def get_internacional(self, vuelo):
        return self._calculados(vuelo)["internacional"]

    def get_margen_min(self, vuelo) -> int:
        return self._calculados(vuelo)["margen_min"]

    @extend_schema_field(serializers.DateTimeField())
    def get_recogida_sugerida(self, vuelo):
        return serializers.DateTimeField().to_representation(self._calculados(vuelo)["recogida_sugerida"])


class HistorialSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.nombre", default=None, read_only=True)

    class Meta:
        model = HistorialEstado
        fields = [
            "estado_anterior",
            "estado_nuevo",
            "actor",
            "usuario",
            "manual",
            "distancia_m",
            "contingencia",
            "creado_en",
        ]


def _ubicacion(direccion, punto) -> dict:
    return {"direccion": direccion, "lat": punto.y, "lon": punto.x}


class ViajeSerializer(serializers.ModelSerializer):
    pasajero = PasajeroResumenSerializer()
    conductor = ConductorResumenSerializer(allow_null=True)
    vehiculo = VehiculoResumenSerializer(allow_null=True)
    convenio = ConvenioResumenSerializer(allow_null=True)
    vuelo = serializers.SerializerMethodField()
    sin_confirmar = serializers.SerializerMethodField()
    alerta_vuelo = serializers.SerializerMethodField(help_text="Alerta de vuelo sin atender (HU-28)")
    en_aeropuerto_a_las = serializers.SerializerMethodField(
        help_text="Salidas: despegue menos la antelación nacional o internacional de la empresa (HU-69)."
    )
    origen = serializers.SerializerMethodField()
    destino = serializers.SerializerMethodField()
    editable = serializers.SerializerMethodField()
    cancelable = serializers.SerializerMethodField()

    class Meta:
        model = Viaje
        fields = [
            "id",
            "estado",
            "canal",
            "folio_contingencia",
            "sentido",
            "pasajero",
            "origen",
            "destino",
            "recogida_en",
            "tarifa",
            "pasajeros",
            "maletas",
            "vuelo_salida_en",
            "vuelo_salida_tipo",
            "vuelo_salida_numero",
            "conductor",
            "vehiculo",
            "convenio",
            "vuelo",
            "alerta_vuelo",
            "en_aeropuerto_a_las",
            "motivo_cancelacion",
            "origen_cancelacion",
            "creado_en",
            "editable",
            "cancelable",
            "confirmar_hasta",
            "sin_confirmar",
            "contacto_correo",
            "empresa_cliente_razon_social",
            "empresa_cliente_rut",
            "empresa_cliente_contacto",
        ]

    @extend_schema_field(serializers.BooleanField())
    def get_sin_confirmar(self, viaje) -> bool:
        """CC-22 (DC-53): pendiente con el plazo vencido; el despacho la confirma o la cancela."""
        from .expiracion import es_sin_confirmar

        return es_sin_confirmar(viaje)

    @extend_schema_field(serializers.ChoiceField(choices=TipoAlertaVuelo.choices, allow_null=True))
    def get_alerta_vuelo(self, viaje):
        abiertas = getattr(viaje, "alertas_abiertas", None)
        if abiertas is None:
            abiertas = viaje.alertas_vuelo.filter(atendida_en__isnull=True).order_by("-id")
        return next((a.tipo for a in abiertas), None)

    @extend_schema_field(VueloSerializer(allow_null=True))
    def get_vuelo(self, viaje):
        vuelo = getattr(viaje, "vuelo", None)
        if vuelo is None:
            return None
        return VueloSerializer(vuelo, context={"configuracion": viaje.empresa.configuracion}).data

    @extend_schema_field(serializers.DateTimeField(allow_null=True))
    def get_en_aeropuerto_a_las(self, viaje):
        from apps.aeropuerto.informacion import en_aeropuerto_a_las

        hora = en_aeropuerto_a_las(viaje, viaje.empresa.configuracion)
        return serializers.DateTimeField().to_representation(hora) if hora else None

    @extend_schema_field(UbicacionSerializer)
    def get_origen(self, viaje):
        return _ubicacion(viaje.origen_dir, viaje.origen_geo)

    @extend_schema_field(UbicacionSerializer)
    def get_destino(self, viaje):
        return _ubicacion(viaje.destino_dir, viaje.destino_geo)

    def get_editable(self, viaje) -> bool:
        return viaje.estado in estados.EDITABLES

    def get_cancelable(self, viaje) -> bool:
        return viaje.estado in estados.CANCELABLES


class CierreForzadoSerializer(serializers.Serializer):
    accion = serializers.CharField()
    motivo = serializers.CharField()
    usuario = serializers.CharField()
    creado_en = serializers.DateTimeField()


class ViajeDetalleSerializer(ViajeSerializer):
    historial = HistorialSerializer(many=True, read_only=True)
    calificacion = serializers.SerializerMethodField(help_text="Puntaje del pasajero, de 1 a 5 (RN-14)")

    cierre_forzado = serializers.SerializerMethodField(help_text="Cierre o anulación forzada (HU-05)")

    class Meta(ViajeSerializer.Meta):
        fields = [*ViajeSerializer.Meta.fields, "historial", "calificacion", "cierre_forzado"]

    @extend_schema_field(CierreForzadoSerializer(allow_null=True))
    def get_cierre_forzado(self, viaje):
        registro = (
            Auditoria.objects.filter(
                entidad=Entidad.VIAJE,
                entidad_id=viaje.pk,
                accion__in=("CIERRE_FORZADO", "ANULACION_FORZADA"),
            )
            .select_related("usuario")
            .order_by("-id")
            .first()
        )
        if registro is None:
            return None
        return {
            "accion": registro.accion,
            "motivo": registro.motivo,
            "usuario": registro.usuario.nombre,
            "creado_en": registro.creado_en,
        }

    def get_calificacion(self, viaje) -> int | None:
        calificacion = getattr(viaje, "calificacion", None)
        return calificacion.puntaje if calificacion else None


class PasajeroEntradaSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=80)
    telefono = serializers.CharField(
        max_length=24, help_text="WhatsApp en formato E.164, p. ej. +56912345678."
    )

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        return valor

    def validate_telefono(self, valor):
        telefono = normalizar_telefono(valor)
        validar_telefono_e164(telefono)
        return telefono


class VueloEntradaSerializer(serializers.Serializer):
    numero = serializers.CharField(max_length=8, help_text="Código IATA, p. ej. LA123 o H2 456.")
    hora_programada = serializers.DateTimeField(help_text="Hora programada de llegada.")

    def validate_numero(self, valor):
        return normalizar_numero_vuelo(valor)


def normalizar_numero_vuelo(valor: str | None) -> str | None:
    """«la  123» → «LA 123», validado como código IATA; vacío → None (HU-69: el de salida es opcional)."""
    numero = " ".join((valor or "").upper().split())
    if not numero:
        return None
    validar_vuelo_iata(numero)
    return numero


def numero_de_salida(**opciones):
    """HU-69: número del vuelo de salida, opcional y sin monitoreo (solo viajes al aeropuerto)."""
    return serializers.CharField(
        max_length=8,
        required=False,
        allow_null=True,
        allow_blank=True,
        help_text="Número del vuelo de salida (opcional, solo viajes al aeropuerto; no se monitorea).",
        **opciones,
    )


@extend_schema_field(OpenApiTypes.INT)
class _ConvenioDeLaEmpresa(serializers.PrimaryKeyRelatedField):
    """Solo convenios activos de la empresa del usuario (RN-08, RN-13)."""

    def get_queryset(self):
        return Convenio.objects.filter(
            empresa_id=self.context["request"].user.empresa_id, estado=EstadoConvenio.APROBADO
        )


class ViajeCrearSerializer(serializers.Serializer):
    pasajero = PasajeroEntradaSerializer()
    canal = serializers.ChoiceField(
        choices=[Canal.TELEFONO, Canal.WHATSAPP, Canal.CONVENIO], default=Canal.TELEFONO
    )
    convenio = _ConvenioDeLaEmpresa(required=False, allow_null=True)
    sentido = serializers.ChoiceField(choices=Sentido.choices, default=Sentido.URBANO)
    origen_dir = serializers.CharField(max_length=200)
    destino_dir = serializers.CharField(max_length=200)
    recogida_en = serializers.DateTimeField()
    tarifa = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    vuelo = VueloEntradaSerializer(required=False, allow_null=True)
    vuelo_salida_numero = numero_de_salida()

    def validate_vuelo_salida_numero(self, valor):
        return normalizar_numero_vuelo(valor)

    def validate(self, datos):
        if datos.get("vuelo_salida_numero") and datos["sentido"] != Sentido.HACIA_AEROPUERTO:
            raise serializers.ValidationError(
                {"vuelo_salida_numero": "El vuelo de salida solo se informa en viajes al aeropuerto."}
            )
        if datos["canal"] == Canal.CONVENIO and not datos.get("convenio"):
            raise serializers.ValidationError(
                {"convenio": "Indica el convenio para una reserva corporativa."}
            )
        if datos.get("convenio") and datos["canal"] != Canal.CONVENIO:
            raise serializers.ValidationError(
                {"canal": "Una reserva con convenio debe tener canal CONVENIO."}
            )
        for campo in ("origen_dir", "destino_dir"):
            datos[campo] = datos[campo].strip()
            if not datos[campo]:
                raise serializers.ValidationError({campo: "La dirección no puede estar vacía."})
        return datos


class ViajeEditarSerializer(serializers.Serializer):
    sentido = serializers.ChoiceField(choices=Sentido.choices, required=False)
    origen_dir = serializers.CharField(max_length=200, required=False)
    destino_dir = serializers.CharField(max_length=200, required=False)
    recogida_en = serializers.DateTimeField(required=False)
    tarifa = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    vuelo = VueloEntradaSerializer(required=False, allow_null=True)
    vuelo_salida_numero = numero_de_salida()

    def validate_vuelo_salida_numero(self, valor):
        return normalizar_numero_vuelo(valor)

    def validate(self, datos):
        for campo in ("origen_dir", "destino_dir"):
            if campo in datos:
                datos[campo] = datos[campo].strip()
                if not datos[campo]:
                    raise serializers.ValidationError({campo: "La dirección no puede estar vacía."})
        return datos


class CancelarSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=200)

    def validate_motivo(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Indica el motivo de la cancelación.")
        return valor


class ForzarCierreSerializer(serializers.Serializer):
    """HU-05. Anular exige motivo; cerrar exige además método y monto (RN-10, RN-11)."""

    accion = serializers.ChoiceField(choices=["ANULAR", "CERRAR"])
    motivo = serializers.CharField(max_length=200, help_text="Queda en auditoría (RN-11)")
    metodo = serializers.ChoiceField(choices=MetodoPago.choices, required=False)
    monto = serializers.IntegerField(min_value=0, max_value=MONTO_MAXIMO, required=False)

    def validate_motivo(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Indica el motivo.")
        return valor

    def validate(self, datos):
        if datos["accion"] == "CERRAR":
            faltan = {
                c: ["Es obligatorio para cerrar el viaje."] for c in ("metodo", "monto") if c not in datos
            }
            if faltan:
                raise serializers.ValidationError(faltan)
        return datos


class AsignarSerializer(serializers.Serializer):
    conductor = serializers.IntegerField(help_text="Conductor Disponible de la empresa (RN-01, RN-03)")


class DecidirRecogidaSerializer(serializers.Serializer):
    recogida_propuesta = serializers.DateTimeField(
        help_text="La hora que vio el despachador: si cambió, responde 409 y no la aplica."
    )


class CandidatoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    patente = serializers.CharField()
    distancia_m = serializers.IntegerField(allow_null=True, help_text="Desde su última posición al origen")
    posicion_en = serializers.DateTimeField(allow_null=True)
    confiable = serializers.BooleanField(
        help_text="Posición reciente y precisa: si no, no compite ni se sugiere"
    )
    ultimo_viaje_en = serializers.DateTimeField(allow_null=True, help_text="Fin de su último viaje")
    posicion_fila = serializers.IntegerField(
        allow_null=True, help_text="Lugar en la fila del aeropuerto (HU-29)"
    )
    sugerido = serializers.BooleanField(
        help_text="El más apto (HU-04). No asigna: lo confirma el despachador"
    )


class ReservaContingenciaSerializer(serializers.Serializer):
    """HU-32 (DC-33): viaje anotado durante una caída, con sus horas reales."""

    folio = serializers.RegexField(
        r"^[A-Za-z0-9-]{1,20}$", help_text="Folio de la hoja de contingencia; único en la empresa"
    )
    pasajero = PasajeroEntradaSerializer()
    sentido = serializers.ChoiceField(choices=Sentido.choices, default=Sentido.URBANO)
    origen_dir = serializers.CharField(max_length=200)
    destino_dir = serializers.CharField(max_length=200)
    tarifa = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    resultado = serializers.ChoiceField(choices=[EstadoViaje.FINALIZADO, EstadoViaje.CANCELADO])
    recogida_en = serializers.DateTimeField(help_text="Hora real de recogida (o la pedida, si se canceló)")
    termino_en = serializers.DateTimeField(help_text="Hora real de término o de cancelación")
    conductor = serializers.IntegerField(required=False, allow_null=True, help_text="Obligatorio si finalizó")
    metodo = serializers.ChoiceField(choices=MetodoPago.choices, required=False, allow_null=True)
    monto = serializers.IntegerField(min_value=0, max_value=MONTO_MAXIMO, required=False, allow_null=True)
    motivo = serializers.CharField(
        max_length=200, required=False, allow_blank=True, help_text="Si se canceló"
    )

    def validate_folio(self, valor):
        return valor.upper()
