"""Settings de pytest (se fijan con `--ds` en pyproject.toml, por encima de cualquier variable de entorno).

Las tareas corren en el mismo proceso, y el broker en memoria impide llegar al worker de desarrollo: sus IDs
son de la base de pruebas, y allá correrían contra la base de desarrollo. Se fija aquí porque Celery lee esta
configuración de settings: cambiarla después, desde un conftest, no perdura.
"""

from .settings import *  # noqa: F403

CELERY_TASK_ALWAYS_EAGER = True
CELERY_BROKER_URL = "memory://"
