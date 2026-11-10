from django.contrib import admin

from .models import Convenio


@admin.register(Convenio)
class ConvenioAdmin(admin.ModelAdmin):
    list_display = ["cliente_nombre", "cliente_rut", "empresa", "estado"]
    list_filter = ["empresa", "estado"]
    raw_id_fields = ["usuario", "revisado_por"]
