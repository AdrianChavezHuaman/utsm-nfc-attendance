"""Configuración de la aplicación.

El prototipo es local: SQLite dentro de instance/ y sin servicios externos.
Las variables de entorno permiten sobreescribir valores sin tocar el código.
"""

import os
from datetime import timedelta
from pathlib import Path
from typing import ClassVar

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"


def _booleano(nombre: str, defecto: str = "0") -> bool:
    """Lee un indicador de entorno como verdadero o falso."""
    return os.environ.get(nombre, defecto).strip().lower() in {"1", "true", "si", "sí", "yes"}


class Config:
    """Configuración por defecto (desarrollo local)."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "shaula-efc-dev-key-cambiar-en-produccion")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'asistencia.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict] = {"pool_pre_ping": True}

    # Subida de sustentos y exportaciones (fases 3 y 4)
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
    UPLOAD_FOLDER = str(INSTANCE_DIR / "uploads")
    EXPORT_FOLDER = str(INSTANCE_DIR / "exports")

    # Sesión / CSRF
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _booleano("SESSION_COOKIE_SECURE")
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    WTF_CSRF_ENABLED = True

    # Seguridad de acceso
    SESSION_IDLE_MINUTES = int(os.environ.get("SESSION_IDLE_MINUTES", "30"))
    MAX_INTENTOS_LOGIN = int(os.environ.get("MAX_INTENTOS_LOGIN", "5"))
    BLOQUEO_MINUTOS = int(os.environ.get("BLOQUEO_MINUTOS", "15"))

    # Marca del prototipo
    APP_NAME = "Control de Asistencia"
    APP_ENTITY = "UTSM"
    APP_VERSION = "0.7.0"
