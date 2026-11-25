from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0019_cc27_apariencia"),
    ]

    operations = [
        migrations.AddField(
            model_name="empresa",
            name="nombre_marca",
            field=models.CharField(blank=True, db_default="", default="", max_length=30),
        ),
        migrations.AddField(
            model_name="empresa",
            name="iniciales",
            field=models.CharField(blank=True, db_default="", default="", max_length=3),
        ),
    ]
