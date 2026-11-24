"""Blueprint de administración de catálogos y usuarios."""

from flask import Blueprint

admin_bp = Blueprint("admin", __name__, template_folder="../templates")


@admin_bp.context_processor
def _entidades_admin():
    from .registry import ENTIDADES

    return {"entidades_admin": ENTIDADES}


from . import routes  # noqa: E402,F401
