from rest_framework import serializers

from .models import Empresa, Usuario


class ErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=120)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)


class EmpresaResumenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = ["id", "razon_social", "slug"]


class UsuarioSesionSerializer(serializers.ModelSerializer):
    empresa = EmpresaResumenSerializer(read_only=True)
    debe_aceptar_privacidad = serializers.SerializerMethodField(
        help_text="DC-44: pasajero con cuenta que debe aceptar el aviso de privacidad vigente."
    )

    class Meta:
        model = Usuario
        fields = [
            "id",
            "nombre",
            "email",
            "rol",
            "empresa",
            "debe_cambiar_password",
            "debe_aceptar_privacidad",
        ]
        read_only_fields = ["debe_cambiar_password"]

    def get_debe_aceptar_privacidad(self, usuario) -> bool:
        from apps.reservas.cuentas_pasajero import debe_aceptar_privacidad

        return debe_aceptar_privacidad(usuario)


class AccessSerializer(serializers.Serializer):
    access = serializers.CharField()


class SesionPanelSerializer(AccessSerializer):
    usuario = UsuarioSesionSerializer()


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class SesionAppSerializer(SesionPanelSerializer):
    refresh = serializers.CharField()


class TokensSerializer(AccessSerializer):
    refresh = serializers.CharField()


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
    password_nueva = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)
