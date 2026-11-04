from django.contrib.gis import admin

from .models import FilaAeropuerto, Geocerca


@admin.register(Geocerca)
class GeocercaAdmin(admin.GISModelAdmin):
    """El polígono del aeropuerto es un supuesto configurable por empresa (DC-21)."""

    list_display = ["nombre", "empresa"]
    list_filter = ["empresa"]


@admin.register(FilaAeropuerto)
class FilaAeropuertoAdmin(admin.ModelAdmin):
    list_display = ["conductor", "geocerca", "ingreso_en", "salida_en", "motivo_salida"]
    list_filter = ["geocerca", "motivo_salida"]
    readonly_fields = ["geocerca", "conductor", "ingreso_en", "salida_en", "motivo_salida"]
