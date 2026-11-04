"""Celery: worker y beat. Las tareas de cada app viven en `tareas.py`; la configuración, en CELERY_*."""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("flotaagil")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks(related_name="tareas")
