"""Rutas de preconsolidado, exportaciones y cierre."""

import io

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from ..extensions import db
from ..kiosk.rules import periodo_bloqueado
from ..models import Consolidado, Incidencia
from ..utils.audit import registrar_auditoria
from ..utils.decorators import roles_required
from . import reports_bp
from .annual import (
    construir_anual,
    generar_csv_anual,
    generar_excel_anual,
    generar_pdf_anual,
    opciones_anuales,
)
from .service import (
    cerrar_periodo,
    construir_resumen,
    corregir_excepcion,
    generar_csv_planilla,
    generar_excel_detallado,
    generar_pdf_reporte,
    listar_periodos,
    obtener_periodo,
    opciones_periodos,
    periodo_por_defecto,
    validar_periodo,
)


def _periodo_solicitado(usar_form: bool = False) -> tuple[int, int]:
    fuente = request.form if usar_form else request.args
    anio = fuente.get("anio", type=int)
    mes = fuente.get("mes", type=int)
    if not anio or not mes:
        anio, mes = periodo_por_defecto()
    try:
        validar_periodo(anio, mes)
    except ValueError:
        abort(404)
    return anio, mes


def _opciones(anio: int, mes: int) -> list[tuple[int, int]]:
    opciones = opciones_periodos()
    if (anio, mes) not in opciones:
        opciones.append((anio, mes))
        opciones.sort(reverse=True)
    return opciones


@reports_bp.route("/consolidado")
@login_required
def index():
    if current_user.rol == "analista":
        return redirect(url_for("reports.preconsolidado"))
    if current_user.rol == "jefe":
        return redirect(url_for("reports.cierre"))
    if current_user.rol == "admin":
        return redirect(url_for("reports.periodos"))
    abort(403)


@reports_bp.route("/preconsolidado")
@roles_required("analista", "jefe", "admin")
def preconsolidado():
    anio, mes = _periodo_solicitado()
    periodo = obtener_periodo(anio, mes, crear=True)
    resumen = construir_resumen(anio, mes)
    return render_template(
        "reports/preconsolidado.html",
        periodo=periodo,
        resumen=resumen,
        opciones=_opciones(anio, mes),
        anio=anio,
        mes=mes,
        puede_corregir=(current_user.rol == "analista" and not periodo_bloqueado(periodo.estado)),
    )


@reports_bp.post("/preconsolidado/<int:anio>/<int:mes>/excepciones/<int:incidencia_id>/corregir")
@roles_required("analista")
def corregir(anio: int, mes: int, incidencia_id: int):
    incidencia = db.session.get(Incidencia, incidencia_id)
    if incidencia is None or incidencia.marca is None:
        abort(404)
    if incidencia.marca.fecha_hora.year != anio or incidencia.marca.fecha_hora.month != mes:
        abort(404)
    ok, mensaje = corregir_excepcion(
        incidencia,
        current_user,
        request.form.get("nota", ""),
    )
    flash(mensaje, "success" if ok else "error")
    return redirect(url_for("reports.preconsolidado", anio=anio, mes=mes))


@reports_bp.route("/cierre", methods=["GET", "POST"])
@roles_required("jefe")
def cierre():
    if request.method == "POST":
        anio, mes = _periodo_solicitado(usar_form=True)
        if not request.form.get("confirmar"):
            flash("Marca la confirmación antes de autorizar el cierre.", "warning")
            return redirect(url_for("reports.cierre", anio=anio, mes=mes))
        ok, mensaje, _periodo = cerrar_periodo(anio, mes, current_user)
        flash(mensaje, "success" if ok else "error")
        return redirect(url_for("reports.cierre", anio=anio, mes=mes))

    anio, mes = _periodo_solicitado()
    periodo = obtener_periodo(anio, mes, crear=True)
    resumen = construir_resumen(anio, mes)
    return render_template(
        "reports/cierre.html",
        periodo=periodo,
        resumen=resumen,
        opciones=_opciones(anio, mes),
        anio=anio,
        mes=mes,
        puede_cerrar=not periodo_bloqueado(periodo.estado),
    )


def _filtros_anual() -> dict:
    anio = request.args.get("anio", type=int) or 2026
    if anio not in (2024, 2025, 2026, 2027):
        anio = 2026
    vista = request.args.get("vista", "anual").strip().lower()
    if vista not in {"anual", "s1", "s2"}:
        vista = "anual"
    return {
        "anio": anio,
        "sede": request.args.get("sede", type=int),
        "area": request.args.get("area", type=int),
        "tipo": request.args.get("tipo", "").strip(),
        "vista": vista,
    }


@reports_bp.route("/consolidado-anual")
@roles_required("analista", "jefe", "admin")
def anual():
    filtros = _filtros_anual()
    datos = construir_anual(
        filtros["anio"],
        sede_id=filtros["sede"],
        area_id=filtros["area"],
        tipo=filtros["tipo"] or None,
        vista=filtros["vista"],
    )
    export_args = {"anio": filtros["anio"]}
    if filtros["sede"]:
        export_args["sede"] = filtros["sede"]
    if filtros["area"]:
        export_args["area"] = filtros["area"]
    if filtros["tipo"]:
        export_args["tipo"] = filtros["tipo"]
    if filtros["vista"] != "anual":
        export_args["vista"] = filtros["vista"]
    vista_args = {"anio": filtros["anio"]}
    if filtros["sede"]:
        vista_args["sede"] = filtros["sede"]
    if filtros["area"]:
        vista_args["area"] = filtros["area"]
    if filtros["tipo"]:
        vista_args["tipo"] = filtros["tipo"]
    return render_template(
        "reports/anual.html",
        datos=datos,
        filtros=filtros,
        opciones=opciones_anuales(),
        export_args=export_args,
        vista_args=vista_args,
    )


@reports_bp.route("/consolidado-anual/exportar")
@roles_required("analista", "jefe", "admin")
def anual_exportar():
    filtros = _filtros_anual()
    formato = request.args.get("formato", "csv").lower()
    if formato not in {"csv", "excel", "pdf"}:
        abort(400)
    datos = construir_anual(
        filtros["anio"],
        sede_id=filtros["sede"],
        area_id=filtros["area"],
        tipo=filtros["tipo"] or None,
        vista=filtros["vista"],
    )
    sufijo = "" if filtros["vista"] == "anual" else f"_{filtros['vista']}"
    if formato == "csv":
        contenido = generar_csv_anual(datos)
        archivo = io.BytesIO(contenido)
        nombre = f"consolidado_anual_{filtros['anio']}{sufijo}.csv"
        mimetype = "text/csv; charset=utf-8"
    elif formato == "excel":
        archivo = generar_excel_anual(datos)
        nombre = f"consolidado_anual_{filtros['anio']}{sufijo}.xlsx"
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        contenido = generar_pdf_anual(datos)
        archivo = io.BytesIO(contenido)
        nombre = f"consolidado_anual_{filtros['anio']}{sufijo}.pdf"
        mimetype = "application/pdf"

    try:
        registrar_auditoria(
            "EXPORTACION",
            "periodo",
            None,
            datos_nuevos={
                "anual": filtros["anio"],
                "formato": formato,
                "sede": filtros["sede"],
                "area": filtros["area"],
                "tipo": filtros["tipo"] or "todos",
                "vista": filtros["vista"],
            },
            id_usuario=current_user.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar la exportación anual.")

    return send_file(
        archivo,
        mimetype=mimetype,
        as_attachment=True,
        download_name=nombre,
    )


@reports_bp.route("/periodos")
@roles_required("analista", "jefe", "admin")
def periodos():
    lista = listar_periodos()
    totales = {}
    for periodo in lista:
        if periodo.estado == "abierto":
            resumen = construir_resumen(periodo.anio, periodo.mes)
            totales[periodo.id_periodo] = {
                "horas": resumen["total_horas"],
                "incidencias": resumen["total_incidencias"],
                "excepciones": resumen["total_excepciones"],
            }
        else:
            totales[periodo.id_periodo] = {
                "horas": periodo.total_horas,
                "incidencias": periodo.total_incidencias,
                "excepciones": periodo.total_excepciones,
            }
    return render_template(
        "reports/periodos.html",
        periodos=lista,
        totales=totales,
    )


@reports_bp.route("/exportar")
@roles_required("analista", "jefe")
def exportar():
    anio, mes = _periodo_solicitado()
    formato = request.args.get("formato", "csv").lower()
    if formato not in {"csv", "excel", "pdf"}:
        abort(400)

    resumen = construir_resumen(anio, mes)
    if formato == "csv":
        contenido = generar_csv_planilla(anio, mes, resumen)
        archivo = io.BytesIO(contenido)
        nombre = f"planilla_{anio}_{mes:02d}.csv"
        mimetype = "text/csv; charset=utf-8"
    elif formato == "excel":
        archivo = generar_excel_detallado(anio, mes, resumen)
        nombre = f"consolidado_{anio}_{mes:02d}.xlsx"
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        contenido = generar_pdf_reporte(anio, mes, resumen)
        archivo = io.BytesIO(contenido)
        nombre = f"reporte_{anio}_{mes:02d}.pdf"
        mimetype = "application/pdf"

    try:
        registrar_auditoria(
            "EXPORTACION",
            "periodo",
            None,
            datos_nuevos={"periodo": f"{mes:02d}/{anio}", "formato": formato},
            id_usuario=current_user.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar la exportación.")

    return send_file(
        archivo,
        mimetype=mimetype,
        as_attachment=True,
        download_name=nombre,
    )


@reports_bp.get("/consolidados/<int:consolidado_id>/descargar")
@roles_required("analista", "jefe", "admin")
def descargar_consolidado(consolidado_id: int):
    consolidado = db.session.get(Consolidado, consolidado_id)
    if consolidado is None:
        abort(404)
    return send_from_directory(
        current_app.config["EXPORT_FOLDER"],
        consolidado.archivo,
        as_attachment=True,
        download_name=consolidado.archivo,
    )
