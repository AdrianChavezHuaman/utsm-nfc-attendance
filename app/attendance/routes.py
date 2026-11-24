"""Rutas de asistencia diaria, personal y ficha individual."""

from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..models import Marca, Trabajador
from ..utils.decorators import roles_required
from . import attendance_bp
from .forms import CorreccionMarcaForm
from .service import (
    corregir_marca as aplicar_correccion,
)
from .service import (
    estado_mes_periodo,
    ficha_trabajador,
    listar_marcas_mes,
    listar_personal,
    opciones_filtros,
    parse_fecha,
    puede_ver_trabajador,
    resumen_dia,
)

ROLES_ASISTENCIA = ("coordinador", "analista", "jefe", "admin")
ROLES_PERSONAL = ("trabajador", "coordinador", "analista", "jefe", "admin")
ROLES_CORRECCION = ("analista", "jefe", "admin")


def _query_args() -> dict:
    return {clave: valor for clave, valor in request.args.items() if clave != "pagina"}


def _filtros_asistencia() -> dict:
    return {
        "fecha": parse_fecha(request.args.get("fecha")),
        "sede": request.args.get("sede", type=int),
        "area": request.args.get("area", type=int),
        "tipo": request.args.get("tipo", "").strip(),
        "q": request.args.get("q", "").strip(),
    }


@attendance_bp.route("/asistencia")
@roles_required(*ROLES_ASISTENCIA)
def asistencia():
    if current_user.rol == "coordinador" and current_user.trabajador is None:
        abort(403)
    filtros = _filtros_asistencia()
    datos = resumen_dia(
        filtros["fecha"],
        current_user,
        sede_id=filtros["sede"],
        area_id=filtros["area"],
        tipo=filtros["tipo"] or None,
        q=filtros["q"],
        pagina=request.args.get("pagina", 1, type=int),
    )
    return render_template(
        "attendance/index.html",
        datos=datos,
        filtros=filtros,
        opciones=opciones_filtros(),
        query_args=_query_args(),
    )


@attendance_bp.route("/mi-asistencia")
@roles_required("trabajador")
def mi_asistencia():
    if current_user.trabajador is None:
        abort(404)
    return redirect(
        url_for(
            "attendance.personal_detalle",
            trabajador_id=current_user.trabajador.id_trabajador,
            **_query_args(),
        )
    )


@attendance_bp.route("/personal")
@roles_required("coordinador", "analista", "jefe", "admin")
def personal():
    if current_user.rol == "coordinador" and current_user.trabajador is None:
        abort(403)
    datos = listar_personal(
        current_user,
        q=request.args.get("q", "").strip(),
        area_id=request.args.get("area", type=int),
        tipo=request.args.get("tipo", "").strip() or None,
        estado=request.args.get("estado", "activos"),
        pagina=request.args.get("pagina", 1, type=int),
    )
    return render_template(
        "attendance/personal.html",
        datos=datos,
        opciones=opciones_filtros(),
        query_args=_query_args(),
        filtros={
            "q": request.args.get("q", "").strip(),
            "area": request.args.get("area", type=int),
            "tipo": request.args.get("tipo", "").strip(),
            "estado": request.args.get("estado", "activos"),
        },
    )


@attendance_bp.route("/personal/<int:trabajador_id>")
@roles_required(*ROLES_PERSONAL)
def personal_detalle(trabajador_id: int):
    trabajador = db.session.get(Trabajador, trabajador_id)
    if trabajador is None:
        abort(404)
    if not puede_ver_trabajador(current_user, trabajador):
        abort(403)

    anio = request.args.get("anio", type=int) or date.today().year
    mes = request.args.get("mes", type=int) or date.today().month
    if not 2000 <= anio <= 2100:
        anio = date.today().year
    if not 1 <= mes <= 12:
        mes = date.today().month
    vista = request.args.get("vista", "calendario")
    if vista not in {"calendario", "lista"}:
        vista = "calendario"

    datos = ficha_trabajador(trabajador, anio, mes)
    return render_template(
        "attendance/detalle.html",
        datos=datos,
        vista=vista,
        es_propio=current_user.rol == "trabajador",
        puede_corregir=current_user.rol in ROLES_CORRECCION,
        query_args=_query_args(),
    )


def _anio_mes_marcas() -> tuple[int, int]:
    anio = request.args.get("anio", type=int) or date.today().year
    mes = request.args.get("mes", type=int) or date.today().month
    if not 2000 <= anio <= 2100:
        anio = date.today().year
    if not 1 <= mes <= 12:
        mes = date.today().month
    return anio, mes


@attendance_bp.route("/personal/<int:trabajador_id>/marcas")
@roles_required(*ROLES_CORRECCION)
def marcas(trabajador_id: int):
    """Listado mensual de marcaciones con acceso a la corrección manual."""
    trabajador = db.session.get(Trabajador, trabajador_id)
    if trabajador is None:
        abort(404)
    anio, mes = _anio_mes_marcas()
    datos = listar_marcas_mes(trabajador, anio, mes)
    return render_template("attendance/marcas.html", datos=datos)


@attendance_bp.route(
    "/personal/<int:trabajador_id>/marcas/<int:marca_id>/corregir",
    methods=["GET", "POST"],
)
@roles_required(*ROLES_CORRECCION)
def corregir_marca(trabajador_id: int, marca_id: int):
    """Corrige una marcación con motivo obligatorio y auditoría."""
    trabajador = db.session.get(Trabajador, trabajador_id)
    if trabajador is None:
        abort(404)
    marca = db.session.get(Marca, marca_id)
    if marca is None or marca.id_trabajador != trabajador.id_trabajador:
        abort(404)

    estado = estado_mes_periodo(marca.fecha_hora.year, marca.fecha_hora.month)
    if estado["bloqueado"]:
        flash(
            f"El periodo de {marca.fecha_hora:%m/%Y} está {estado['estado']} "
            "y no admite correcciones.",
            "error",
        )
        return redirect(
            url_for(
                "attendance.marcas",
                trabajador_id=trabajador.id_trabajador,
                anio=marca.fecha_hora.year,
                mes=marca.fecha_hora.month,
            )
        )

    form = CorreccionMarcaForm()
    if request.method == "GET":
        form.fecha.data = marca.fecha_hora.date()
        form.hora.data = marca.fecha_hora.time().replace(second=0, microsecond=0)
        form.tipo.data = marca.tipo

    if form.validate_on_submit():
        ok, mensaje = aplicar_correccion(
            marca,
            current_user,
            form.fecha.data,
            form.hora.data,
            form.tipo.data,
            form.motivo.data,
        )
        flash(mensaje, "success" if ok else "error")
        if ok:
            return redirect(
                url_for(
                    "attendance.marcas",
                    trabajador_id=trabajador.id_trabajador,
                    anio=marca.fecha_hora.year,
                    mes=marca.fecha_hora.month,
                )
            )

    return render_template(
        "attendance/corregir_marca.html",
        datos=listar_marcas_mes(trabajador, marca.fecha_hora.year, marca.fecha_hora.month),
        marca=marca,
        form=form,
    )
