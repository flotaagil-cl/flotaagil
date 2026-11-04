"""Zona por defecto de la fila para las empresas que ya existen (DC-21). Las nuevas la configuran en el admin."""

from django.contrib.gis.geos import Polygon
from django.db import migrations

# Copia de apps.aeropuerto.zonas: una migración no debe depender de código que puede cambiar.
ESQUINAS_SCL = ((-70.82, -33.42), (-70.76, -33.42), (-70.76, -33.37), (-70.82, -33.37), (-70.82, -33.42))


def crear(apps, schema_editor):
    Empresa = apps.get_model("cuentas", "Empresa")
    Geocerca = apps.get_model("aeropuerto", "Geocerca")
    for empresa in Empresa.objects.all():
        Geocerca.objects.get_or_create(
            empresa=empresa, nombre="Aeropuerto SCL", defaults={"poligono": Polygon(ESQUINAS_SCL, srid=4326)}
        )


class Migration(migrations.Migration):
    dependencies = [
        ("aeropuerto", "0003_geocerca_y_fila"),
        ("cuentas", "__first__"),
    ]

    operations = [migrations.RunPython(crear, migrations.RunPython.noop)]
