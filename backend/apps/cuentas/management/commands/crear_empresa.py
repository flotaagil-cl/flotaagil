"""Alta de un cliente nuevo (DC-38): EMPRESA, su CONFIGURACION_EMPRESA y su primer ADMINISTRADOR.

    python manage.py crear_empresa --rut 76543210-3 --razon-social "Taxis Ejemplo SpA" --slug taxis-ejemplo \\
        --plan ESTANDAR --admin-email admin@taxis-ejemplo.cl --admin-nombre "Nombre Apellido" [--geocerca-scl]

Funciona en producción (no exige DEBUG). Todo va en una transacción: si el RUT, el slug o el correo ya
existen, o algún dato no es válido, no crea nada. La contraseña temporal del administrador (DC-14: vence a las
72 h y obliga a cambiarla) se imprime una sola vez y no queda en ningún registro.
"""

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.auditoria import servicios as auditoria
from apps.auditoria.models import Entidad
from apps.comun.validadores import normalizar_rut, validar_kebab, validar_rut
from apps.cuentas.credenciales import nueva_password_temporal
from apps.cuentas.models import Empresa, Plan, Rol, Usuario


class Command(BaseCommand):
    help = "Da de alta a un cliente: empresa, configuración por defecto y su primer administrador."

    def add_arguments(self, parser):
        parser.add_argument("--rut", required=True, help="RUT de la empresa, 12345678-9 (con o sin puntos)")
        parser.add_argument("--razon-social", required=True)
        parser.add_argument("--slug", required=True, help="Identificador del portal en kebab-case")
        parser.add_argument("--plan", required=True, choices=Plan.values)
        parser.add_argument("--admin-email", required=True)
        parser.add_argument("--admin-nombre", required=True)
        parser.add_argument(
            "--geocerca-scl", action="store_true", help="Agrega la geocerca del aeropuerto SCL"
        )

    def handle(self, *args, **o):
        rut = normalizar_rut(o["rut"])
        razon_social = o["razon_social"].strip()
        slug = o["slug"].strip()
        email = o["admin_email"].strip().lower()
        nombre = o["admin_nombre"].strip()
        errores = []
        for etiqueta, validar, valor in (
            ("RUT", validar_rut, rut),
            ("slug", validar_kebab, slug),
            ("correo del administrador", validate_email, email),
        ):
            try:
                validar(valor)
            except ValidationError as error:
                errores.append(f"{etiqueta}: {' '.join(error.messages)}")
        if not razon_social:
            errores.append("razón social: no puede estar vacía.")
        if not nombre:
            errores.append("nombre del administrador: no puede estar vacío.")
        if Empresa.objects.filter(rut=rut).exists():
            errores.append(f"RUT: ya existe una empresa con el RUT {rut}.")
        if Empresa.objects.filter(slug=slug).exists():
            errores.append(f"slug: ya existe una empresa con el slug «{slug}».")
        if Usuario.objects.filter(email__iexact=email).exists():
            errores.append(
                "correo del administrador: ya tiene una cuenta (el correo es único en el sistema, PR-15)."
            )
        if errores:
            raise CommandError("No se creó nada.\n  - " + "\n  - ".join(errores))

        with transaction.atomic():
            empresa = Empresa.objects.create(rut=rut, razon_social=razon_social, slug=slug, plan=o["plan"])
            password = nueva_password_temporal()
            admin = Usuario(empresa=empresa, email=email, nombre=nombre, rol=Rol.ADMINISTRADOR)
            admin.set_password(password)
            admin.debe_cambiar_password = True
            admin.password_temporal_vence = timezone.now() + timedelta(hours=settings.PASSWORD_TEMPORAL_HORAS)
            admin.save()
            if o["geocerca_scl"]:
                from apps.aeropuerto.models import Geocerca
                from apps.aeropuerto.zonas import NOMBRE_ZONA_SCL, poligono_scl

                Geocerca.objects.create(empresa=empresa, nombre=NOMBRE_ZONA_SCL, poligono=poligono_scl())
            # Sin usuario autenticado: el evento queda a nombre del sistema (como DC-27).
            auditoria.registrar(
                usuario=None,
                empresa_id=empresa.pk,
                entidad=Entidad.USUARIO,
                entidad_id=admin.pk,
                accion="ALTA_EMPRESA",
                datos_previos={"plan": empresa.plan, "geocerca_scl": bool(o["geocerca_scl"])},
            )

        self.stdout.write(self.style.SUCCESS(f"Empresa «{empresa.razon_social}» creada (id {empresa.pk})."))
        self.stdout.write(f"Portal: /solicitar/{empresa.slug}")
        self.stdout.write(f"Administrador: {admin.email}")
        self.stdout.write(f"Contraseña temporal (se muestra una sola vez): {password}")
        self.stdout.write(
            f"Vence el {timezone.localtime(admin.password_temporal_vence):%d-%m-%Y %H:%M}; "
            "al entrar deberá cambiarla."
        )
