"""HU-31 (CC-12): pasa el último turno de DC-26 (`turno_inicio`, `turno_fin`) a TURNO y retira esas columnas.

- Turno abierto: conductor en turno (Disponible o En viaje). Si no tenía `turno_inicio` (p. ej. datos cargados
  sin pasar por la app), se abre con la hora de la migración. Vehículo: el declarado.
- Turno terminado: `turno_inicio` y `turno_fin` con motivo CONDUCTOR (DC-26 no guardaba el motivo). Vehículo: el
  del último viaje del conductor en esa ventana, o NULL si no se sabe.
- Los viajes ACEPTADO o posteriores del conductor quedan en el turno migrado si los aceptó dentro de él (según
  HISTORIAL_ESTADO), o si están en ejecución con el turno abierto.
- Los turnos anteriores al último no existen: DC-26 no los guardaba.

La reversa repone `turno_inicio` y `turno_fin` desde el último TURNO de cada conductor.
"""

from django.db import migrations
from django.db.models import OuterRef, Subquery
from django.utils import timezone

EN_TURNO = ("DISPONIBLE", "EN_VIAJE")
EN_EJECUCION = ("ACEPTADO", "EN_CAMINO", "EN_ZONA", "PASAJERO_A_BORDO")


def adelante(apps, schema_editor):
    Conductor = apps.get_model("flota", "Conductor")
    Turno = apps.get_model("flota", "Turno")
    Viaje = apps.get_model("reservas", "Viaje")
    HistorialEstado = apps.get_model("reservas", "HistorialEstado")
    ahora = timezone.now()
    aceptado_en = HistorialEstado.objects.filter(viaje=OuterRef("pk"), estado_nuevo="ACEPTADO").values("creado_en")[:1]
    for conductor in Conductor.objects.all():
        en_turno = conductor.estado in EN_TURNO
        if en_turno:
            turno = Turno.objects.create(
                conductor=conductor,
                vehiculo_id=conductor.vehiculo_activo_id,
                hora_inicio=conductor.turno_inicio or ahora,
            )
        elif conductor.turno_inicio is not None:
            fin = max(conductor.turno_fin or conductor.turno_inicio, conductor.turno_inicio)
            ultimo = (
                Viaje.objects.filter(conductor=conductor, vehiculo__isnull=False, recogida_en__lte=fin)
                .order_by("-recogida_en")
                .first()
            )
            turno = Turno.objects.create(
                conductor=conductor,
                vehiculo_id=ultimo.vehiculo_id if ultimo else None,
                hora_inicio=conductor.turno_inicio,
                hora_termino=fin,
                motivo_termino="CONDUCTOR",
            )
        else:
            continue
        viajes = Viaje.objects.filter(conductor=conductor, turno__isnull=True).annotate(aceptado_en=Subquery(aceptado_en))
        dentro = viajes.filter(aceptado_en__gte=turno.hora_inicio)
        if turno.hora_termino is not None:
            dentro = dentro.filter(aceptado_en__lte=turno.hora_termino)
        ids = set(dentro.values_list("pk", flat=True))
        if en_turno:
            ids |= set(viajes.filter(estado__in=EN_EJECUCION).values_list("pk", flat=True))
        Viaje.objects.filter(pk__in=ids).update(turno=turno)


def atras(apps, schema_editor):
    Conductor = apps.get_model("flota", "Conductor")
    Turno = apps.get_model("flota", "Turno")
    Viaje = apps.get_model("reservas", "Viaje")
    for conductor in Conductor.objects.all():
        ultimo = Turno.objects.filter(conductor=conductor).order_by("-hora_inicio", "-id").first()
        if ultimo is not None:
            conductor.turno_inicio, conductor.turno_fin = ultimo.hora_inicio, ultimo.hora_termino
            conductor.save(update_fields=["turno_inicio", "turno_fin"])
    Viaje.objects.update(turno=None)
    apps.get_model("flota", "CierreCaja").objects.all().delete()
    Turno.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("flota", "0005_turno_cierre_caja"),
        ("reservas", "0010_viaje_turno"),
    ]

    operations = [
        migrations.RunPython(adelante, atras),
        migrations.RemoveField(model_name="conductor", name="turno_fin"),
        migrations.RemoveField(model_name="conductor", name="turno_inicio"),
    ]
