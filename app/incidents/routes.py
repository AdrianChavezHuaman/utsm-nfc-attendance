"""Rutas de incidencias, justificaciones y aprobaciones."""

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..models import ESTADOS_INCIDENCIA, Area, Incidencia, Justificacion, Trabajador
from ..utils.decorators import roles_required
from . import incidents_bp
from .forms import DecisionForm, JustificacionForm
from .service import (
    en_plazo,
    puede_justificar,
    puede_resolver,
    puede_ver,
    registrar_justificacion,
    resolver_justificacion,
    resumen_justificaciones,
)


def _incidencia_o_404(incidencia_id: int) -> Incidencia:
    incidencia = db.session.get(Incidencia, incidencia_id)
    if incidencia is None:
        abort(404)
    return incidencia


def _volver_url() -> str:
    if current_user.rol == "trabajador":
        return url_for("incidents.mis_incidencias")
    if current_user.rol == "coordinador":
        return url_for("incidents.bandeja")
    return url_for("incidents.index")


@incidents_bp.route("/incidencias")
@login_required
def index():
    """Bandeja global para analista, jefe y admin; redirige a cada rol."""
    if current_user.rol == "trabajador":
        return redirect(url_for("incidents.mis_incidencias"))
    if current_user.rol == "coordinador":
        return redirect(url_for("incidents.bandeja"))
    if current_user.rol not in {"analista", "jefe", "admin"}:
        abort(403)

    estado = request.args.get("estado", "").strip()
    area_id = request.args.get("area", type=int)

    consulta = Incidencia.query
    if estado in ESTADOS_INCIDENCIA:
        consulta = consulta.filter(Incidencia.estado == estado)
    if area_id:
        consulta = consulta.join(
            Trabajador, Incidencia.id_trabajador == Trabajador.id_trabajador
        ).filter(Trabajador.id_area == area_id)

    incidencias = (
        consulta.order_by(Incidencia.fecha_creacion.desc(), Incidencia.id_incidencia.desc())
        .limit(100)
        .all()
    )
    return render_template(
        "incidents/index.html",
        incidencias=incidencias,
        areas=Area.query.order_by(Area.nombre).all(),
        resumen=resumen_justificaciones(current_user),
        estados=ESTADOS_INCIDENCIA,
        estado_seleccionado=estado,
        area_seleccionada=area_id,
    )


@incidents_bp.route("/mis-incidencias")
@roles_required("trabajador")
def mis_incidencias():
    incidencias = (
        Incidencia.query.filter_by(id_trabajador=current_user.id_trabajador)
        .order_by(Incidencia.fecha_creacion.desc(), Incidencia.id_incidencia.desc())
        .all()
    )
    return render_template(
        "incidents/mis_incidencias.html",
        incidencias=incidencias,
        resumen=resumen_justificaciones(current_user),
    )


@incidents_bp.route("/bandeja-coordinador")
@roles_required("coordinador")
def bandeja():
    area = current_user.trabajador.area if current_user.trabajador else None
    if area is None:
        abort(403)

    pendientes = (
        Justificacion.query.join(
            Incidencia, Justificacion.id_incidencia == Incidencia.id_incidencia
        )
        .join(Trabajador, Incidencia.id_trabajador == Trabajador.id_trabajador)
        .filter(
            Trabajador.id_area == area.id_area,
            Justificacion.estado == "enviada",
        )
        .order_by(Justificacion.fecha_envio.asc())
        .all()
    )
    incidencias_area = (
        Incidencia.query.join(Trabajador, Incidencia.id_trabajador == Trabajador.id_trabajador)
        .filter(Trabajador.id_area == area.id_area)
        .order_by(Incidencia.fecha_creacion.desc())
        .limit(40)
        .all()
    )
    return render_template(
        "incidents/bandeja_coordinador.html",
        area=area,
        pendientes=pendientes,
        incidencias_area=incidencias_area,
        resumen=resumen_justificaciones(current_user),
    )


@incidents_bp.route("/incidencias/<int:incidencia_id>")
@login_required
def detalle(incidencia_id: int):
    incidencia = _incidencia_o_404(incidencia_id)
    if not puede_ver(current_user, incidencia):
        abort(403)

    return render_template(
        "incidents/detalle.html",
        incidencia=incidencia,
        justificacion=incidencia.justificacion,
        puede_justificar=puede_justificar(current_user, incidencia),
        puede_resolver=puede_resolver(current_user, incidencia),
        en_plazo=en_plazo(incidencia),
        form=DecisionForm(),
        volver_url=_volver_url(),
    )


@incidents_bp.route("/incidencias/<int:incidencia_id>/justificar", methods=["GET", "POST"])
@roles_required("trabajador")
def justificar(incidencia_id: int):
    incidencia = _incidencia_o_404(incidencia_id)
    if not puede_ver(current_user, incidencia):
        abort(403)

    if not en_plazo(incidencia):
        flash("El plazo de cinco días hábiles para justificar venció.", "warning")
        return redirect(url_for("incidents.detalle", incidencia_id=incidencia.id_incidencia))
    if not puede_justificar(current_user, incidencia):
        flash("Esta incidencia ya no requiere una nueva justificación.", "warning")
        return redirect(url_for("incidents.detalle", incidencia_id=incidencia.id_incidencia))

    form = JustificacionForm()
    if form.validate_on_submit():
        ok, mensaje, _justificacion = registrar_justificacion(
            incidencia,
            current_user,
            form.motivo.data,
            form.archivo.data,
        )
        flash(mensaje, "success" if ok else "error")
        if ok:
            return redirect(url_for("incidents.detalle", incidencia_id=incidencia.id_incidencia))
    elif request.method == "GET" and incidencia.justificacion is not None:
        form.motivo.data = incidencia.justificacion.motivo

    return render_template(
        "incidents/justificar.html",
        incidencia=incidencia,
        justificacion=incidencia.justificacion,
        form=form,
        es_reenvio=(
            incidencia.justificacion is not None and incidencia.justificacion.estado == "rechazada"
        ),
    )


@incidents_bp.post("/incidencias/<int:incidencia_id>/resolver")
@roles_required("coordinador")
def resolver(incidencia_id: int):
    incidencia = _incidencia_o_404(incidencia_id)
    if not puede_ver(current_user, incidencia):
        abort(403)

    form = DecisionForm()
    if not form.validate_on_submit():
        flash("No se pudo procesar la decisión. Revisa el formulario.", "error")
        return redirect(url_for("incidents.detalle", incidencia_id=incidencia.id_incidencia))

    if form.aprobar.data:
        decision = "aprobar"
    elif form.rechazar.data:
        decision = "rechazar"
    else:
        decision = None

    ok, mensaje, _justificacion = resolver_justificacion(
        incidencia,
        current_user,
        decision or "",
        form.comentario.data,
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("incidents.detalle", incidencia_id=incidencia.id_incidencia))


@incidents_bp.get("/incidencias/<int:incidencia_id>/sustento")
@login_required
def sustento(incidencia_id: int):
    incidencia = _incidencia_o_404(incidencia_id)
    if not puede_ver(current_user, incidencia):
        abort(403)
    justificacion = incidencia.justificacion
    if justificacion is None or not justificacion.archivo:
        abort(404)
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        justificacion.archivo,
        as_attachment=False,
        download_name=justificacion.nombre_archivo or justificacion.archivo,
    )
