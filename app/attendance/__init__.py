"""Blueprint de asistencia diaria y fichas de personal."""

from flask import Blueprint

attendance_bp = Blueprint("attendance", __name__, template_folder="../templates")

from . import routes  # noqa: E402,F401
