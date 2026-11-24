"""Rutas del kiosco público de marcación."""

from datetime import datetime

from flask import jsonify, render_template, request
from flask_login import current_user

from ..models import Lector, Sede, Tarjeta, Trabajador
from ..utils.helpers import fecha_legible
from . import kiosk_bp
from .service import registrar_marcacion


def _contexto() -> dict:
    sedes = Sede.query.filter_by(activa=True).order_by(Sede.id_sede).all()
    lectores = (
        Lector.query.filter_by(estado="activo")
        .order_by(Lector.id_sede, Lector.tipo, Lector.id_lector)
        .all()
    )
    tarjetas = []
    if (
        current_user.is_authenticated
        and current_user.trabajador
        and current_user.trabajador.tarjeta
    ):
        tarjetas.append(current_user.trabajador.tarjeta)
    tarjetas_ids = {tarjeta.id_tarjeta for tarjeta in tarjetas}
    for tipo, cantidad in (("admin", 3), ("docente_tc", 3), ("docente_tp", 2)):
        for tarjeta in (
            Tarjeta.query.join(Trabajador, Tarjeta.id_trabajador == Trabajador.id_trabajador)
            .filter(Tarjeta.estado == "activa", Trabajador.tipo == tipo)
            .order_by(Tarjeta.id_tarjeta)
            .limit(cantidad)
            .all()
        ):
            if tarjeta.id_tarjeta not in tarjetas_ids:
                tarjetas.append(tarjeta)
                tarjetas_ids.add(tarjeta.id_tarjeta)
    tarjetas = tarjetas[:9]
    tarjetas_demo = [
        {
            "uid": tarjeta.uid,
            "nombre": tarjeta.trabajador.nombre_corto,
            "area": tarjeta.trabajador.area.nombre,
        }
        for tarjeta in tarjetas
        if tarjeta.trabajador is not None
    ]
    return {
        "sedes": sedes,
        "lectores": lectores,
        "tarjetas_demo": tarjetas_demo,
        "hoy_legible": fecha_legible(),
        "hora_actual": datetime.now().strftime("%H:%M:%S"),
    }


@kiosk_bp.route("/kiosk", methods=["GET", "POST"])
def index():
    """Pantalla pública del kiosco. El POST es el respaldo sin JavaScript."""
    contexto = _contexto()
    resultado = None
    if request.method == "POST":
        resultado = registrar_marcacion(
            request.form.get("uid"),
            request.form.get("tipo"),
            request.form.get("id_lector", type=int),
        )
    return render_template(
        "kiosk/index.html",
        resultado=resultado,
        **contexto,
    )


@kiosk_bp.post("/api/marca")
def api_marca():
    """Registro de marcación para el kiosco con JavaScript."""
    datos = request.get_json(silent=True) or {}
    resultado = registrar_marcacion(
        datos.get("uid"),
        datos.get("tipo"),
        datos.get("id_lector"),
    )
    return jsonify(resultado)
