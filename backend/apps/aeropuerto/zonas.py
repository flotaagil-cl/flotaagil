"""Zona por defecto de la fila (DC-21). SUPUESTO: un rectángulo aproximado alrededor del Aeropuerto Arturo
Merino Benítez, no su límite real. Se ajusta por empresa desde el admin (GEOCERCA)."""

from django.contrib.gis.geos import Polygon

NOMBRE_ZONA_SCL = "Aeropuerto SCL"
ESQUINAS_SCL = ((-70.82, -33.42), (-70.76, -33.42), (-70.76, -33.37), (-70.82, -33.37), (-70.82, -33.42))


def poligono_scl() -> Polygon:
    return Polygon(ESQUINAS_SCL, srid=4326)
