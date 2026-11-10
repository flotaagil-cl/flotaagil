from rest_framework import serializers

from apps.comun.validadores import normalizar_rut, validar_rut

from .models import Convenio


class ConvenioSerializer(serializers.ModelSerializer):
    reservas = serializers.IntegerField(read_only=True, help_text="Reservas hechas con este convenio")
    tiene_cuenta = serializers.SerializerMethodField(help_text="Si la empresa cliente tiene cuenta (HU-34)")

    class Meta:
        model = Convenio
        fields = ["id", "cliente_nombre", "cliente_rut", "estado", "activo", "tiene_cuenta", "reservas"]
        read_only_fields = fields

    def get_tiene_cuenta(self, convenio) -> bool:
        return convenio.usuario_id is not None


class ConvenioDetalleSerializer(ConvenioSerializer):
    encargado_email = serializers.EmailField(
        source="usuario.email", allow_null=True, default=None, read_only=True
    )
    revisado_por = serializers.CharField(
        source="revisado_por.nombre", allow_null=True, default=None, read_only=True
    )

    class Meta(ConvenioSerializer.Meta):
        fields = [
            *ConvenioSerializer.Meta.fields,
            "direccion",
            "encargado_nombre",
            "encargado_email",
            "encargado_telefono",
            "motivo_rechazo",
            "revisado_por",
            "revisado_en",
            "creado_en",
        ]
        read_only_fields = fields


def _rut(valor):
    valor = normalizar_rut(valor)
    try:
        validar_rut(valor)
    except Exception as error:
        raise serializers.ValidationError(getattr(error, "message", "RUT inválido.")) from error
    return valor


def _texto(valor):
    valor = (valor or "").strip()
    if not valor:
        raise serializers.ValidationError("No puede estar vacío.")
    return valor


TELEFONO = r"^\+[1-9]\d{7,14}$"


class _DatosConvenio(serializers.Serializer):
    cliente_nombre = serializers.CharField(max_length=120)
    cliente_rut = serializers.CharField(max_length=14, help_text="12345678-9, con o sin puntos")
    direccion = serializers.CharField(max_length=200, required=False, allow_null=True, allow_blank=True)
    encargado_nombre = serializers.CharField(max_length=80, required=False, allow_null=True, allow_blank=True)
    encargado_telefono = serializers.RegexField(
        TELEFONO, max_length=16, required=False, allow_null=True, allow_blank=True
    )

    def validate_cliente_nombre(self, valor):
        return _texto(valor)

    def validate_cliente_rut(self, valor):
        return _rut(valor)


class ConvenioCrearSerializer(_DatosConvenio):
    """Convenio sin cuenta, para las reservas que ingresa la central (HU-34: el administrador no crea
    cuentas)."""


class ConvenioEditarSerializer(_DatosConvenio):
    pass


class RechazoSerializer(serializers.Serializer):
    motivo = serializers.CharField(max_length=200)


class RegistroConvenioSerializer(serializers.Serializer):
    """HU-34: formulario público de registro de la empresa cliente."""

    cliente_nombre = serializers.CharField(max_length=120, help_text="Razón social")
    cliente_rut = serializers.CharField(max_length=14)
    direccion = serializers.CharField(max_length=200)
    encargado_nombre = serializers.CharField(max_length=80)
    email = serializers.EmailField(max_length=120)
    encargado_telefono = serializers.RegexField(TELEFONO, max_length=16)
    password = serializers.CharField(max_length=128, write_only=True, style={"input_type": "password"})
    sitio_web = serializers.CharField(
        required=False, allow_blank=True, help_text="Campo trampa: debe ir vacío"
    )

    def validate_cliente_nombre(self, valor):
        return _texto(valor)

    def validate_direccion(self, valor):
        return _texto(valor)

    def validate_encargado_nombre(self, valor):
        return _texto(valor)

    def validate_cliente_rut(self, valor):
        return _rut(valor)


class RegistroAuditoriaSerializer(serializers.Serializer):
    """HU-12: quién, qué y cuándo. Sin datos previos: el criterio pide usuario, acción y fecha."""

    id = serializers.IntegerField()
    accion = serializers.CharField()
    usuario = serializers.CharField(source="usuario.nombre", allow_null=True, default=None)
    creado_en = serializers.DateTimeField()
