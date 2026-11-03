import django_filters
from django.db.models import Q

from .models import Conductor, EstadoConductor, Vehiculo


class VehiculoFiltro(django_filters.FilterSet):
    activo = django_filters.BooleanFilter()
    q = django_filters.CharFilter(method="buscar", help_text="Patente o marca y modelo")

    class Meta:
        model = Vehiculo
        fields = []

    def buscar(self, queryset, nombre, valor):
        valor = valor.strip()
        if not valor:
            return queryset
        patente = "".join(c for c in valor if c.isalnum()).upper()
        return queryset.filter(Q(patente__icontains=patente or valor) | Q(marca_modelo__icontains=valor))


class ConductorFiltro(django_filters.FilterSet):
    estado = django_filters.ChoiceFilter(choices=EstadoConductor.choices)
    activo = django_filters.BooleanFilter(field_name="usuario__activo", help_text="Cuenta habilitada")
    q = django_filters.CharFilter(method="buscar", help_text="Nombre, RUT, email o patente asociada")

    class Meta:
        model = Conductor
        fields = []

    def buscar(self, queryset, nombre, valor):
        valor = valor.strip()
        if not valor:
            return queryset
        rut = valor.replace(".", "").upper()
        return queryset.filter(
            Q(usuario__nombre__icontains=valor)
            | Q(usuario__email__icontains=valor)
            | Q(rut__icontains=rut)
            | Q(asociaciones__vehiculo__patente__icontains=valor.replace("-", "").upper())
        ).distinct()
