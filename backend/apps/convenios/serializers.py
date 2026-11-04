from rest_framework import serializers

from apps.comun.validadores import normalizar_rut, validar_rut

from .models import Convenio


class ConvenioSerializer(serializers.ModelSerializer):
    reservas = serializers.IntegerField(read_only=True, help_text="Reservas hechas con este convenio")

    class Meta:
        model = Convenio
        fields = ["id", "cliente_nombre", "cliente_rut", "activo", "reservas"]
        read_only_fields = fields


class ConvenioDetalleSerializer(ConvenioSerializer):
    """Incluye el token del link: es una credencial, por eso no va en el listado."""

    class Meta(ConvenioSerializer.Meta):
        fields = [*ConvenioSerializer.Meta.fields, "token_link"]
        read_only_fields = fields


class _DatosConvenio(serializers.Serializer):
    cliente_nombre = serializers.CharField(max_length=120)
    cliente_rut = serializers.CharField(max_length=14, help_text="12345678-9, con o sin puntos")

    def validate_cliente_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("El nombre no puede estar vacío.")
        return valor

    def validate_cliente_rut(self, valor):
        valor = normalizar_rut(valor)
        try:
            validar_rut(valor)
        except Exception as error:
            raise serializers.ValidationError(getattr(error, "message", "RUT inválido.")) from error
        return valor


class ConvenioCrearSerializer(_DatosConvenio):
    pass


class ConvenioEditarSerializer(_DatosConvenio):
    activo = serializers.BooleanField(help_text="False invalida el link sin borrar el historial (RN-08)")


class ConvenioCreadoSerializer(ConvenioDetalleSerializer):
    password = serializers.CharField(read_only=True, help_text="Se entrega una sola vez")

    class Meta(ConvenioDetalleSerializer.Meta):
        fields = [*ConvenioDetalleSerializer.Meta.fields, "password"]
        read_only_fields = fields


class PasswordNuevaSerializer(serializers.Serializer):
    password = serializers.CharField(help_text="Se entrega una sola vez. La anterior deja de servir.")


class RegistroAuditoriaSerializer(serializers.Serializer):
    """HU-12: quién, qué y cuándo. Sin datos previos: el criterio pide usuario, acción y fecha."""

    id = serializers.IntegerField()
    accion = serializers.CharField()
    usuario = serializers.CharField(source="usuario.nombre", allow_null=True, default=None)
    creado_en = serializers.DateTimeField()
