from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.comun.validadores import (
    normalizar_rut,
    normalizar_telefono,
    validar_movil_chile,
    validar_patente,
    validar_rut,
)
from apps.cuentas.credenciales import estado_de_acceso
from apps.cuentas.models import Usuario
from apps.reservas.serializers import ConductorResumenSerializer

from .models import Conductor, Vehiculo

PATENTE_REGISTRADA = "Esta patente ya está registrada."
RUT_REGISTRADO = "Este RUT ya está registrado."
EMAIL_REGISTRADO = "Este correo ya tiene una cuenta."


def normalizar_patente(valor: str) -> str:
    """«ab-12·34», «AB 1234» o «ab.1234» → «AB1234»."""
    return "".join(c for c in (valor or "") if c.isalnum()).upper()


class PatenteField(serializers.CharField):
    def to_internal_value(self, data):
        return normalizar_patente(super().to_internal_value(data))


class VehiculoSerializer(serializers.ModelSerializer):
    conductores = serializers.SerializerMethodField()

    class Meta:
        model = Vehiculo
        fields = ["id", "patente", "marca_modelo", "anio", "capacidad", "activo", "conductores"]

    @staticmethod
    @extend_schema_field(ConductorResumenSerializer(many=True))
    def get_conductores(vehiculo):
        asociados = [a.conductor for a in vehiculo.asociaciones.all()]
        return ConductorResumenSerializer(sorted(asociados, key=lambda c: c.usuario.nombre), many=True).data


class VehiculoCrearSerializer(serializers.ModelSerializer):
    patente = PatenteField(
        max_length=12,
        help_text="Se normaliza: sin guiones, puntos ni espacios y en mayúsculas.",
        validators=[UniqueValidator(Vehiculo.objects.all(), message=PATENTE_REGISTRADA)],
    )

    class Meta:
        model = Vehiculo
        fields = ["patente", "marca_modelo", "anio", "capacidad"]

    def validate_patente(self, valor):
        # El campo declarado reemplaza al del modelo: el formato se valida después de normalizar.
        validar_patente(valor)
        return valor

    def validate_marca_modelo(self, valor):
        return " ".join(valor.split())


class VehiculoEditarSerializer(serializers.ModelSerializer):
    """La patente no se edita: otra patente es otro vehículo."""

    class Meta:
        model = Vehiculo
        fields = ["marca_modelo", "anio", "capacidad", "activo"]

    def validate_marca_modelo(self, valor):
        return " ".join(valor.split())


class VehiculoAsociadoSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="vehiculo.id")
    patente = serializers.CharField(source="vehiculo.patente")
    marca_modelo = serializers.CharField(source="vehiculo.marca_modelo")
    activo = serializers.BooleanField(source="vehiculo.activo")
    desde = serializers.DateField()


class VehiculoDeclaradoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    patente = serializers.CharField()


class ConductorSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(source="usuario.nombre", read_only=True)
    email = serializers.EmailField(source="usuario.email", read_only=True)
    activo = serializers.BooleanField(source="usuario.activo", read_only=True, help_text="Cuenta habilitada")
    licencia_vigente = serializers.SerializerMethodField()
    acceso = serializers.SerializerMethodField(
        help_text="SIN_PASSWORD (recién creada), TEMPORAL (debe cambiarla), TEMPORAL_VENCIDA o ACTIVA."
    )
    password_temporal_vence = serializers.DateTimeField(
        source="usuario.password_temporal_vence", read_only=True, allow_null=True
    )
    vehiculo_activo = VehiculoDeclaradoSerializer(allow_null=True, read_only=True)
    vehiculos = serializers.SerializerMethodField()

    class Meta:
        model = Conductor
        fields = [
            "id",
            "nombre",
            "email",
            "activo",
            "rut",
            "telefono",
            "licencia_clase",
            "licencia_vence",
            "licencia_vigente",
            "estado",
            "vehiculo_activo",
            "consentimiento_gps_en",
            "acceso",
            "password_temporal_vence",
            "vehiculos",
        ]
        read_only_fields = fields

    @staticmethod
    @extend_schema_field(
        serializers.ChoiceField(choices=["SIN_PASSWORD", "TEMPORAL", "TEMPORAL_VENCIDA", "ACTIVA"])
    )
    def get_acceso(conductor):
        return estado_de_acceso(conductor.usuario)

    @staticmethod
    def get_licencia_vigente(conductor) -> bool:
        return conductor.licencia_vence > timezone.localdate()

    @staticmethod
    @extend_schema_field(VehiculoAsociadoSerializer(many=True))
    def get_vehiculos(conductor):
        asociaciones = sorted(conductor.asociaciones.all(), key=lambda a: a.vehiculo.patente)
        return VehiculoAsociadoSerializer(asociaciones, many=True).data


class ConductorEditarSerializer(serializers.Serializer):
    """Datos del conductor. El email y la contraseña (credenciales) no se editan aquí."""

    nombre = serializers.CharField(max_length=80)
    rut = serializers.CharField(max_length=14, help_text="Acepta puntos y la K minúscula.")
    telefono = serializers.CharField(
        max_length=24, help_text="Móvil chileno: +569XXXXXXXX (sin prefijo, 9XXXXXXXX también sirve)."
    )
    licencia_clase = serializers.ChoiceField(choices=Conductor._meta.get_field("licencia_clase").choices)
    licencia_vence = serializers.DateField()

    def validate_nombre(self, valor):
        valor = " ".join(valor.split())
        if not valor:
            raise serializers.ValidationError("No puede estar vacío.")
        return valor

    def validate_rut(self, valor):
        valor = normalizar_rut(valor)
        validar_rut(valor)
        otros = Conductor.objects.filter(rut=valor)
        if self.context.get("conductor") is not None:
            otros = otros.exclude(pk=self.context["conductor"].pk)
        if otros.exists():
            raise serializers.ValidationError(RUT_REGISTRADO)
        return valor

    def validate_telefono(self, valor):
        valor = normalizar_telefono(valor)
        # Un móvil chileno escrito sin prefijo (9 dígitos que empiezan con 9, como en una planilla).
        if len(valor) == 9 and valor.startswith("9") and valor.isdigit():
            valor = f"+56{valor}"
        validar_movil_chile(valor)
        return valor

    def validate_licencia_vence(self, valor):
        if valor <= timezone.localdate():
            raise serializers.ValidationError(
                "La licencia debe estar vigente: la fecha tiene que ser futura."
            )
        return valor


class ConductorCrearSerializer(ConductorEditarSerializer):
    """Alta: los datos del conductor más el correo de acceso. La cuenta queda sin contraseña utilizable."""

    email = serializers.EmailField(max_length=120)

    def validate_email(self, valor):
        valor = valor.strip().lower()
        if Usuario.objects.filter(email__iexact=valor).exists():
            raise serializers.ValidationError(EMAIL_REGISTRADO)
        return valor


class PasswordTemporalSerializer(serializers.Serializer):
    password_temporal = serializers.CharField(
        help_text="Se muestra una sola vez. No se guarda en texto plano."
    )
    vence_en = serializers.DateTimeField()


class AsociarVehiculoSerializer(serializers.Serializer):
    vehiculo = serializers.PrimaryKeyRelatedField(queryset=Vehiculo.objects.none())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # RN-13: solo vehículos de la empresa; uno ajeno responde «no existe».
        if "empresa" in self.context:
            self.fields["vehiculo"].queryset = Vehiculo.objects.filter(empresa=self.context["empresa"])


class FilaImportacionSerializer(serializers.Serializer):
    linea = serializers.IntegerField(help_text="Línea del archivo (la 1 es el encabezado)")
    datos = serializers.DictField(child=serializers.CharField(allow_blank=True))
    errores = serializers.DictField(child=serializers.ListField(child=serializers.CharField()))


class InformeImportacionSerializer(serializers.Serializer):
    filas = FilaImportacionSerializer(many=True)
    validas = serializers.IntegerField()
    con_errores = serializers.IntegerField()
    creados = serializers.IntegerField()


class ImportarSerializer(serializers.Serializer):
    archivo = serializers.FileField(
        help_text="CSV en UTF-8 o Windows-1252, separado por coma o punto y coma."
    )
    confirmar = serializers.BooleanField(
        default=False, help_text="false: solo valida y muestra el informe. true: crea si no hay errores."
    )
