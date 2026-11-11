from rest_framework import serializers

from apps.comun.validadores import normalizar_telefono, validar_telefono_e164, validar_vuelo_iata
from apps.cuentas.models import Empresa
from apps.reservas.models import MAX_PASAJEROS, Sentido, TipoVuelo


class EmpresaPublicaSerializer(serializers.ModelSerializer):
    anticipacion_minima_min = serializers.IntegerField(source="configuracion.anticipacion_minima_min")
    expiracion_verificacion_min = serializers.IntegerField(source="configuracion.expiracion_verificacion_min")
    margen_nacional_min = serializers.IntegerField(
        source="configuracion.margen_nacional_min",
        help_text="Minutos que se suman a la llegada del vuelo cuando no se indica la recogida (RN-17).",
    )
    antelacion_vuelo_nacional_min = serializers.IntegerField(
        source="configuracion.antelacion_vuelo_nacional_min",
        help_text="Al aeropuerto: minutos antes de un vuelo nacional para la recogida sugerida (DC-42).",
    )
    antelacion_vuelo_internacional_min = serializers.IntegerField(
        source="configuracion.antelacion_vuelo_internacional_min",
        help_text="Al aeropuerto: minutos antes de un vuelo internacional para la recogida sugerida (DC-42).",
    )
    capacidad_maxima = serializers.SerializerMethodField(
        help_text="Pasajeros por viaje: capacidad del vehículo activo más grande; null sin vehículos (DC-43)."
    )

    class Meta:
        model = Empresa
        fields = [
            "razon_social",
            "slug",
            "anticipacion_minima_min",
            "expiracion_verificacion_min",
            "margen_nacional_min",
            "antelacion_vuelo_nacional_min",
            "antelacion_vuelo_internacional_min",
            "capacidad_maxima",
        ]

    def get_capacidad_maxima(self, empresa) -> int | None:
        from .servicios import capacidad_maxima

        return capacidad_maxima(empresa)


class VueloLlegadaSerializer(serializers.Serializer):
    numero = serializers.CharField(max_length=8, help_text="Código IATA, p. ej. LA123 o H2 456.")
    hora_llegada = serializers.DateTimeField(
        required=False, help_text="Hora programada de llegada del vuelo. Obligatoria si no viene `fecha`."
    )
    fecha = serializers.DateField(
        required=False,
        help_text="HU-39: día de llegada; la hora la da la API de vuelos. Si no responde, se pide la hora.",
    )

    def validate_numero(self, valor):
        numero = " ".join(valor.upper().split())
        validar_vuelo_iata(numero)
        return numero

    def validate(self, datos):
        if "hora_llegada" not in datos and "fecha" not in datos:
            raise serializers.ValidationError({"fecha": "Indica la fecha del vuelo."})
        return datos


class VueloSalidaSerializer(serializers.Serializer):
    """HU-39: vuelo de salida en los viajes al aeropuerto (DC-42)."""

    hora = serializers.DateTimeField(help_text="Hora de salida del vuelo.")
    tipo = serializers.ChoiceField(choices=TipoVuelo.choices)


class SolicitudSerializer(serializers.Serializer):
    """HU-19: solicitud de viaje sin cuenta."""

    nombre = serializers.CharField(max_length=80)
    telefono = serializers.CharField(
        max_length=24, help_text="WhatsApp en formato E.164, p. ej. +56912345678."
    )
    origen_dir = serializers.CharField(max_length=200)
    destino_dir = serializers.CharField(max_length=200)
    recogida_en = serializers.DateTimeField(
        required=False,
        allow_null=True,
        help_text="Obligatoria, salvo en viajes desde el aeropuerto con vuelo: ahí se calcula si no viene.",
    )
    sentido = serializers.ChoiceField(
        choices=Sentido.choices,
        required=False,
        help_text="Si no viene: DESDE_AEROPUERTO cuando hay vuelo, URBANO si no.",
    )
    vuelo = VueloLlegadaSerializer(required=False, help_text="Solo para viajes desde el aeropuerto.")
    vuelo_salida = VueloSalidaSerializer(required=False, help_text="Solo para viajes al aeropuerto (HU-39).")
    lo_antes_posible = serializers.BooleanField(
        required=False,
        default=False,
        help_text="HU-39: recogida ahora + la anticipación mínima (DC-10); ignora `recogida_en`.",
    )
    pasajeros = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        max_value=MAX_PASAJEROS,
        help_text="Titular más acompañantes; no supera la capacidad de la flota (DC-43).",
    )
    maletas = serializers.IntegerField(required=False, default=0, min_value=0, max_value=20)
    acepta_privacidad = serializers.BooleanField()
    acepta_whatsapp = serializers.BooleanField()
    # Campo trampa para bots: el formulario lo oculta; una persona lo deja vacío.
    sitio_web = serializers.CharField(required=False, allow_blank=True, write_only=True)

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Ingresa tu nombre.")
        return valor

    def validate_telefono(self, valor):
        telefono = normalizar_telefono(valor)
        validar_telefono_e164(telefono)
        return telefono

    def validate_acepta_privacidad(self, valor):
        if not valor:
            raise serializers.ValidationError("Debes aceptar el aviso de privacidad.")
        return valor

    def validate_acepta_whatsapp(self, valor):
        if not valor:
            raise serializers.ValidationError(
                "Debes aceptar los avisos por WhatsApp para confirmar tu viaje."
            )
        return valor

    def validate(self, datos):
        for campo in ("origen_dir", "destino_dir"):
            datos[campo] = datos[campo].strip()
            if not datos[campo]:
                raise serializers.ValidationError({campo: "Ingresa la dirección."})
        if datos.get("recogida_en") is None or datos.get("lo_antes_posible"):
            datos.pop("recogida_en", None)  # null del formulario = no informada
        vuelo = datos.get("vuelo")
        salida = datos.get("vuelo_salida")
        sentido = datos.setdefault("sentido", Sentido.DESDE_AEROPUERTO if vuelo else Sentido.URBANO)
        if vuelo and sentido != Sentido.DESDE_AEROPUERTO:
            raise serializers.ValidationError(
                {"vuelo": "El vuelo solo se informa en viajes desde el aeropuerto (llegadas)."}
            )
        if salida and sentido != Sentido.HACIA_AEROPUERTO:
            raise serializers.ValidationError(
                {"vuelo_salida": "El vuelo de salida solo se informa en viajes al aeropuerto."}
            )
        calculada = datos.get("lo_antes_posible") or (vuelo and sentido == Sentido.DESDE_AEROPUERTO) or salida
        if "recogida_en" not in datos and not calculada:
            raise serializers.ValidationError({"recogida_en": "Indica la fecha y hora de recogida."})
        return datos


class SolicitudConvenioSerializer(SolicitudSerializer):
    """HU-34: la cuenta del convenio pide a nombre del pasajero y declara que este autorizó los avisos. La
    declaración queda ligada al usuario que reserva (DC-35)."""

    declara_autorizacion = serializers.BooleanField(
        help_text="Declaro que el pasajero autorizó recibir avisos por WhatsApp"
    )

    def validate_declara_autorizacion(self, valor):
        if not valor:
            raise serializers.ValidationError("Debes declarar que el pasajero autorizó los avisos.")
        return valor


class SolicitudRespuestaSerializer(serializers.Serializer):
    estado = serializers.CharField()
    recogida_en = serializers.DateTimeField()
    expira_en = serializers.DateTimeField(
        allow_null=True,
        help_text="Plazo para confirmar por WhatsApp (RN-06). NULL si el teléfono ya estaba verificado "
        "(DC-31): la reserva queda SOLICITADO sin pedir confirmación.",
    )
    mensaje = serializers.CharField()


class CrearCuentaSerializer(serializers.Serializer):
    """HU-35: cuenta opcional del pasajero en la empresa del portal."""

    nombre = serializers.CharField(max_length=80)
    telefono = serializers.CharField(
        max_length=24, help_text="WhatsApp en formato E.164, p. ej. +56912345678."
    )
    email = serializers.EmailField(max_length=120)
    password = serializers.CharField(max_length=128, write_only=True)
    sitio_web = serializers.CharField(
        required=False, allow_blank=True, help_text="Campo trampa: debe ir vacío"
    )

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Ingresa tu nombre.")
        return valor

    def validate_telefono(self, valor):
        telefono = normalizar_telefono(valor)
        validar_telefono_e164(telefono)
        return telefono
