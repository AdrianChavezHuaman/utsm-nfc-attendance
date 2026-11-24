"""Fábrica de la aplicación Flask del prototipo Shaula_efc."""

from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, logout_user

from .config import Config
from .extensions import csrf, db, login_manager
from .utils.helpers import (
    accion_label,
    estado_incidencia,
    estado_justificacion_label,
    estado_periodo,
    fecha_legible,
    initials,
    miles,
    role_color,
    role_label,
    tipo_incidencia_label,
    tipo_marca_label,
)


def create_app(config_class=Config) -> Flask:
    """Crea e inicializa la aplicación."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Carpetas locales necesarias
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["EXPORT_FOLDER"]).mkdir(parents=True, exist_ok=True)

    # Extensiones
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Blueprints
    from .admin import admin_bp
    from .attendance import attendance_bp
    from .audit import audit_bp
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .incidents import incidents_bp
    from .kiosk import kiosk_bp
    from .main import main_bp
    from .reports import reports_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(audit_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(kiosk_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(reports_bp)

    from .incidents.service import en_plazo, puede_justificar

    app.jinja_env.globals["incidencia_en_plazo"] = en_plazo
    app.jinja_env.globals["usuario_puede_justificar"] = puede_justificar

    # Flask-Login
    @login_manager.user_loader
    def load_user(user_id: str):
        from .models import Usuario

        try:
            return db.session.get(Usuario, int(user_id))
        except (TypeError, ValueError):
            return None

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para continuar."
    login_manager.login_message_category = "warning"
    login_manager.session_protection = "strong"

    # Expiración por inactividad y cabeceras de seguridad
    @app.before_request
    def _expirar_sesion_inactiva():
        """Cierra la sesión cuando pasa el tiempo de inactividad configurado."""
        if request.endpoint == "static" or not current_user.is_authenticated:
            return None
        ahora = datetime.now()
        ultimo = session.get("ultimo_movimiento")
        if ultimo:
            try:
                previo = datetime.fromisoformat(ultimo)
            except (TypeError, ValueError):
                previo = ahora
            if ahora - previo > timedelta(minutes=app.config["SESSION_IDLE_MINUTES"]):
                logout_user()
                session.pop("ultimo_movimiento", None)
                flash("Tu sesión se cerró por inactividad. Vuelve a ingresar.", "warning")
                return redirect(url_for("auth.login"))
        session["ultimo_movimiento"] = ahora.isoformat()
        return None

    @app.after_request
    def _cabeceras_seguridad(respuesta):
        respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
        respuesta.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        respuesta.headers.setdefault("Referrer-Policy", "same-origin")
        respuesta.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if request.endpoint != "static" and current_user.is_authenticated:
            respuesta.headers.setdefault("Cache-Control", "no-store")
        return respuesta

    # Utilidades de plantillas
    app.jinja_env.filters["initials"] = initials
    app.jinja_env.filters["miles"] = miles

    @app.context_processor
    def inject_globals():
        return {
            "current_year": datetime.now().year,
            "hoy_legible": fecha_legible(),
            "role_label": role_label,
            "role_color": role_color,
            "accion_label": accion_label,
            "estado_periodo": estado_periodo,
            "estado_incidencia": estado_incidencia,
            "estado_justificacion_label": estado_justificacion_label,
            "tipo_incidencia_label": tipo_incidencia_label,
            "tipo_marca_label": tipo_marca_label,
        }

    # Manejadores de error
    @app.errorhandler(403)
    def forbidden(_error):
        return (
            render_template(
                "errors/error.html",
                code=403,
                title="Acceso denegado",
                message="Tu rol no tiene permiso para consultar esta sección.",
            ),
            403,
        )

    @app.errorhandler(404)
    def not_found(_error):
        return (
            render_template(
                "errors/error.html",
                code=404,
                title="Página no encontrada",
                message="La dirección que buscas no existe o fue movida.",
            ),
            404,
        )

    @app.errorhandler(413)
    def too_large(_error):
        return (
            render_template(
                "errors/error.html",
                code=413,
                title="Archivo demasiado grande",
                message="El archivo supera el límite permitido de 8 MB.",
            ),
            413,
        )

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return (
            render_template(
                "errors/error.html",
                code=500,
                title="Error interno",
                message="Ocurrió un problema inesperado. Intenta nuevamente.",
            ),
            500,
        )

    # Comandos Flask CLI
    from .cli import register_cli

    register_cli(app)

    return app
