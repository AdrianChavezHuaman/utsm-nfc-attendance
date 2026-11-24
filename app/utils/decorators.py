"""Decoradores de autorización por rol."""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles: str):
    """Permite el acceso solo a los roles indicados.

    Uso:
        @roles_required("analista", "jefe")
        def dashboard(): ...
    """

    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.rol not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapper

    return decorator
