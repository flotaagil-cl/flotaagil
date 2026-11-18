"""Entradas y salidas de la API del chat (CC-19). Las salidas se arman en `servicios`; aquí se describen."""

from rest_framework import serializers

from .models import MAX_TEXTO, RespuestaRapida, TipoConversacion


class MensajeChatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    conversacion = serializers.IntegerField()
    texto = serializers.CharField()
    rapida = serializers.CharField(allow_blank=True)
    autor = serializers.CharField(help_text="En el hilo central el conductor ve al equipo como «Central».")
    propio = serializers.BooleanField()
    creado_en = serializers.DateTimeField()


class UltimoMensajeSerializer(serializers.Serializer):
    texto = serializers.CharField()
    autor = serializers.CharField()
    creado_en = serializers.DateTimeField()


class ConversacionChatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=TipoConversacion.choices)
    titulo = serializers.CharField()
    no_leidos = serializers.IntegerField()
    ultimo = UltimoMensajeSerializer(allow_null=True)
    ultimo_mensaje_en = serializers.DateTimeField(allow_null=True)
    puede_gestionar = serializers.BooleanField(help_text="Grupos: puede renombrar y cambiar integrantes.")
    puede_borrar = serializers.BooleanField(help_text="Grupos: su creador o el administrador.")


class PaginaMensajesSerializer(serializers.Serializer):
    results = MensajeChatSerializer(many=True)
    hay_mas = serializers.BooleanField()
    leido_por_otros_hasta = serializers.IntegerField(
        help_text="Los mensajes propios hasta este id ya se leyeron."
    )


class NuevoMensajeSerializer(serializers.Serializer):
    texto = serializers.CharField(max_length=MAX_TEXTO, required=False, allow_blank=True)
    rapida = serializers.ChoiceField(choices=RespuestaRapida.choices, required=False)

    def validate(self, datos):
        if datos.get("rapida"):
            datos["texto"] = RespuestaRapida(datos["rapida"]).label
        else:
            datos["texto"] = (datos.get("texto") or "").strip()
            if not datos["texto"]:
                raise serializers.ValidationError({"texto": "Escribe un mensaje."}, code="vacio")
        return datos


class LeidoSerializer(serializers.Serializer):
    hasta = serializers.IntegerField(min_value=1)


class PersonaChatSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    rol = serializers.CharField()


class NuevoDirectoSerializer(serializers.Serializer):
    usuario = serializers.IntegerField()


class GrupoSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(max_length=60)
    integrantes = PersonaChatSerializer(many=True, read_only=True)
    creado_por = serializers.CharField(read_only=True, allow_null=True)
    creado_en = serializers.DateTimeField(read_only=True)
    ultimo_mensaje_en = serializers.DateTimeField(read_only=True, allow_null=True)

    def validate_nombre(self, valor):
        valor = valor.strip()
        if not valor:
            raise serializers.ValidationError("Ponle un nombre al grupo.", code="vacio")
        return valor


class NuevoGrupoSerializer(GrupoSerializer):
    ids_integrantes = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, max_length=100, write_only=True
    )


class IntegranteSerializer(serializers.Serializer):
    usuario = serializers.IntegerField()
