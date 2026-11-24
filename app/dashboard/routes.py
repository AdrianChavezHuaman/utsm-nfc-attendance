"""Rutas del panel KPI y de los gráficos."""

from flask import jsonify, render_template, request
from flask_login import current_user

from ..utils.decorators import roles_required
from . import dashboard_bp
from .service import (
    METAS,
    contexto_anio,
    heatmap_historico,
    kpi_anio,
    opciones_filtros,
    operacion_periodo,
    series_historicas,
)

ROLES_KPI = ("analista", "jefe", "admin")


def _filtros() -> dict:
    anios = set(range(2024, 2028))
    anio = request.args.get("anio", type=int) or 2026
    if anio not in anios:
        anio = 2026
    mes = request.args.get("mes", type=int)
    if mes is not None and not 1 <= mes <= 12:
        mes = None
    tipo = request.args.get("tipo", "").strip()
    if tipo not in {"admin", "docente_tc", "docente_tp"}:
        tipo = ""
    return {
        "anio": anio,
        "mes": mes,
        "sede": request.args.get("sede", type=int),
        "area": request.args.get("area", type=int),
        "tipo": tipo,
    }


@dashboard_bp.route("/dashboard")
@roles_required(*ROLES_KPI)
def index():
    filtros = _filtros()
    operacion = operacion_periodo(
        filtros["anio"],
        filtros["mes"],
        filtros["sede"],
        filtros["area"],
        filtros["tipo"] or None,
    )
    return render_template(
        "dashboard/index.html",
        kpis=kpi_anio(filtros["anio"]),
        contexto=contexto_anio(filtros["anio"]),
        operacion=operacion,
        filtros=filtros,
        opciones=opciones_filtros(),
        simulacion=filtros["anio"] == 2027 and operacion["total_marcas"] > 0,
    )


@dashboard_bp.route("/api/kpi")
@roles_required(*ROLES_KPI)
def api_kpi():
    filtros = _filtros()
    return jsonify(
        {
            "anio": filtros["anio"],
            "kpis": kpi_anio(filtros["anio"]),
            "contexto": contexto_anio(filtros["anio"]),
            "proyeccion": filtros["anio"] == 2027,
        }
    )


@dashboard_bp.route("/api/chart-data")
@roles_required(*ROLES_KPI)
def api_chart_data():
    serie = request.args.get("serie", "historico")
    tipo = request.args.get("tipo", "line")
    metrica = request.args.get("metrica", "calidad")
    filtros = _filtros()

    if serie == "operacion":
        operacion = operacion_periodo(
            filtros["anio"],
            filtros["mes"],
            filtros["sede"],
            filtros["area"],
            filtros["tipo"] or None,
        )
        if tipo == "heatmap":
            return jsonify(
                {
                    "serie": "operacion",
                    "tipo": "heatmap",
                    "x_labels": operacion["labels"],
                    "y_labels": ["Marcas", "Incidencias"],
                    "matrix": [operacion["marcas"], operacion["incidencias"]],
                    "units": ["marcas", "incidencias"],
                    "mejor": ["mayor", "menor"],
                    "meta": operacion,
                }
            )
        return jsonify(
            {
                "serie": "operacion",
                "tipo": tipo,
                "labels": operacion["labels"],
                "datasets": [
                    {
                        "label": "Marcaciones",
                        "data": operacion["marcas"],
                        "color": "#1c5a3e",
                    },
                    {
                        "label": "Incidencias",
                        "data": operacion["incidencias"],
                        "color": "#9a4f31",
                    },
                ],
                "meta": {
                    "etiqueta": operacion["etiqueta"],
                    "total_marcas": operacion["total_marcas"],
                    "total_incidencias": operacion["total_incidencias"],
                    "calidad_operativa": operacion["calidad_operativa"],
                    "nfc_adopcion": operacion["nfc_adopcion"],
                    "escenario": "to_be_simulado" if filtros["anio"] == 2027 else "as_is",
                },
            }
        )

    if tipo == "heatmap":
        return jsonify(
            {
                "serie": "historico",
                "tipo": "heatmap",
                **heatmap_historico(),
            }
        )

    serie_historica = series_historicas(metrica)
    return jsonify(
        {
            "serie": "historico",
            "tipo": tipo,
            "metrica": metrica,
            "labels": serie_historica["labels"],
            "datasets": [
                {
                    "label": serie_historica["nombre"],
                    "data": serie_historica["datos"],
                    "color": "#1c5a3e",
                }
            ],
            "meta": {
                "nombre": serie_historica["nombre"],
                "unidad": serie_historica["unidad"],
                "meta": METAS[metrica],
                "2027": "Proyección TO-BE",
            },
            "usuario": current_user.rol,
        }
    )
