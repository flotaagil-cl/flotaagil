"""DC-61 y DC-65 (CC-19, HU-64): activación por correo y teléfono sin verificación.

- `telefono_verificado` queda en true para las cuentas ya confirmadas por WhatsApp: conservan lo que veían.
- Se retiran `telefono_pendiente` y `telefono_pendiente_en`. Un cambio de número pendiente se descarta y la
  cuenta conserva su teléfono vigente (`telefono` no se toca).
"""

from django.db import migrations, models


def marcar_verificadas(apps, schema_editor):
    CuentaPasajero = apps.get_model("reservas", "CuentaPasajero")
    CuentaPasajero.objects.filter(confirmada_en__isnull=False).update(telefono_verificado=True)


class Migration(migrations.Migration):
    dependencies = [
        ("reservas", "0019_dc59_ajustes_cc22"),
    ]

    operations = [
        migrations.AddField(
            model_name="cuentapasajero",
            name="telefono_verificado",
            field=models.BooleanField(db_default=False, default=False),
        ),
        migrations.RunPython(marcar_verificadas, migrations.RunPython.noop),
        migrations.RemoveField(model_name="cuentapasajero", name="telefono_pendiente"),
        migrations.RemoveField(model_name="cuentapasajero", name="telefono_pendiente_en"),
    ]
