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
from apps.reservas.serializers import ConductorResumenSerializer

from .models import Conductor, Vehiculo

PATENTE_REGISTRADA = "Esta patente ya está registrada."
RUT_REGISTRADO = "Este RUT ya está registrado."


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
    nombre = serializers.CharField(source="usuario.nombre")
    email = serializers.EmailField(source="usuario.email")
    activo = serializers.BooleanField(source="usuario.activo", help_text="Cuenta habilitada")
    licencia_vigente = serializers.SerializerMethodField()
    vehiculo_activo = VehiculoDeclaradoSerializer(allow_null=True)
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
            "vehiculos",
        ]
        read_only_fields = fields

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
    telefono = serializers.CharField(max_length=24, help_text="Móvil chileno: +569XXXXXXXX.")
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
        conductor = self.context["conductor"]
        if Conductor.objects.filter(rut=valor).exclude(pk=conductor.pk).exists():
            raise serializers.ValidationError(RUT_REGISTRADO)
        return valor

    def validate_telefono(self, valor):
        valor = normalizar_telefono(valor)
        validar_movil_chile(valor)
        return valor

    def validate_licencia_vence(self, valor):
        if valor <= timezone.localdate():
            raise serializers.ValidationError(
                "La licencia debe estar vigente: la fecha tiene que ser futura."
            )
        return valor


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
