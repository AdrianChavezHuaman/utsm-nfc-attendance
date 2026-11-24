"""Rutas de inicio y cierre de sesión."""

from datetime import datetime

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db
from ..models import Usuario
from ..utils.audit import registrar_auditoria
from ..utils.helpers import is_safe_url
from . import auth_bp
from .forms import LoginForm

# Hash de relleno: mantiene un tiempo similar cuando el correo no existe.
_HASH_FICTICIO = generate_password_hash("shaula-efc-tiempo-constante")

MENSAJE_FALLO = "Credenciales inválidas o cuenta inactiva. Verifica tus datos."


def _autenticar(usuario: Usuario | None, password: str, ahora: datetime) -> bool:
    """Comprueba la contraseña sin revelar si la cuenta existe o está bloqueada."""
    if usuario is None:
        check_password_hash(_HASH_FICTICIO, password)
        return False
    if usuario.esta_bloqueado(ahora):
        usuario.check_password(password)
        return False
    if not usuario.activo:
        usuario.check_password(password)
        return False
    return usuario.check_password(password)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Inicio de sesión con correo institucional y contraseña."""
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))

    form = LoginForm()
    if form.validate_on_submit():
        correo = form.correo.data.strip().lower()
        password = form.password.data
        ahora = datetime.now()
        usuario = Usuario.query.filter_by(correo=correo).first()

        if _autenticar(usuario, password, ahora):
            usuario.reiniciar_intentos()
            usuario.ultimo_acceso = ahora

            # Se limpia la sesión anterior antes de autenticar (fijación de sesión).
            session.clear()
            login_user(usuario, remember=form.recordarme.data)
            session["ultimo_movimiento"] = ahora.isoformat()

            registrar_auditoria(
                "LOGIN",
                "usuario",
                usuario.id_usuario,
                datos_nuevos={"correo": usuario.correo, "rol": usuario.rol},
                id_usuario=usuario.id_usuario,
            )

            siguiente = request.args.get("next")
            if siguiente and is_safe_url(siguiente):
                return redirect(siguiente)
            return redirect(url_for("main.inicio"))

        bloqueo_nuevo = False
        if usuario is not None and usuario.activo and not usuario.esta_bloqueado(ahora):
            bloqueo_nuevo = usuario.registrar_intento_fallido(
                current_app.config["MAX_INTENTOS_LOGIN"],
                current_app.config["BLOQUEO_MINUTOS"],
            )

        registrar_auditoria(
            "LOGIN_FALLIDO",
            "usuario",
            usuario.id_usuario if usuario else None,
            datos_nuevos={
                "correo": correo,
                "intentos": usuario.intentos_fallidos if usuario else 0,
            },
            id_usuario=usuario.id_usuario if usuario else None,
            commit=False,
        )
        if bloqueo_nuevo:
            registrar_auditoria(
                "LOGIN_BLOQUEADO",
                "usuario",
                usuario.id_usuario,
                datos_nuevos={
                    "correo": usuario.correo,
                    "bloqueado_hasta": usuario.bloqueado_hasta.isoformat(),
                    "minutos": current_app.config["BLOQUEO_MINUTOS"],
                },
                id_usuario=usuario.id_usuario,
                commit=False,
            )
        db.session.commit()
        flash(MENSAJE_FALLO, "error")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Cierra la sesión actual y deja constancia en auditoría."""
    usuario_id = current_user.id_usuario
    correo = current_user.correo
    registrar_auditoria("LOGOUT", "usuario", usuario_id, datos_nuevos={"correo": correo})
    logout_user()
    session.pop("ultimo_movimiento", None)
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for("auth.login"))
