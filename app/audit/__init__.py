"""Blueprint del visor de auditoría."""

from flask import Blueprint

audit_bp = Blueprint("audit", __name__, template_folder="../templates")


@audit_bp.context_processor
def _etiquetas_auditoria():
    from .presenter import etiqueta_tabla

    return {"etiqueta_tabla": etiqueta_tabla}


from . import routes  # noqa: E402,F401
