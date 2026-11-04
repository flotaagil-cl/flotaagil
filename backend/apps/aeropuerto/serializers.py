from rest_framework import serializers

from .models import AlertaVuelo


class AlertaVueloSerializer(serializers.ModelSerializer):
    atendida_por = serializers.CharField(
        source="atendida_por.nombre", default=None, allow_null=True, read_only=True
    )

    class Meta:
        model = AlertaVuelo
        fields = [
            "id",
            "viaje",
            "numero_vuelo",
            "tipo",
            "detalle",
            "eta",
            "creada_en",
            "atendida_en",
            "atendida_por",
        ]
        read_only_fields = fields
