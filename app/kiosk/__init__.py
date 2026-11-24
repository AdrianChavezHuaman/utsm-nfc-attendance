"""Blueprint del kiosco de marcación NFC simulado."""

from flask import Blueprint

kiosk_bp = Blueprint("kiosk", __name__, template_folder="../templates")

from . import routes  # noqa: E402,F401
