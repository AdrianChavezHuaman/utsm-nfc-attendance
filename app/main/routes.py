"""Rutas base de la aplicación."""

from datetime import datetime, time, timedelta

from flask import redirect, render_template, url_for
from flask_login import current_user, login_required

from ..incidents.service import resumen_justificaciones
from ..models import (
    Area,
    Auditoria,
    Horario,
    Lector,
    Marca,
    Periodo,
    Sede,
    Tarjeta,
    Trabajador,
    Usuario,
)
from ..reports.service import periodo_por_defecto
from ..utils.helpers import fecha_legible, role_label
from . import main_bp

MENSAJES_ROL = {
    "trabajador": "Revisa tu asistencia y justifica tus incidencias desde el panel. El consolidado lo gestiona RR. HH.",
    "coordinador": "Revisa la asistencia y las justificaciones de tu área. El consolidado y el cierre los gestiona RR. HH.",
    "analista": "El tablero de asistencia, el panel KPI y la línea base 2024–2026 están disponibles; revisa excepciones antes del cierre.",
    "jefe": "El tablero de asistencia y el panel KPI resumen la operación; el preconsolidado está listo para revisión y cierre.",
    "admin": "Gestiona catálogos, tarjetas, lectores y usuarios; la línea base histórica 2024–2026 ya está cargada.",
}

FASES = [
    ("Fase 1", "Fundación: base, seed, login y diseño base", "completada"),
    ("Fase 2", "Kiosco NFC y reglas de marcación R-01 a R-10", "completada"),
    ("Fase 3", "Incidencias, justificaciones y aprobaciones", "completada"),
    ("Fase 4", "Consolidado mensual, exportaciones y cierre", "completada"),
    ("Fase 5", "Dashboard KPI, gráficos, auditoría y administración", "completada"),
    ("Fase 6", "Línea base 2024–2026, pruebas y capturas", "completada"),
]


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.inicio"))
    return redirect(url_for("auth.login"))


@main_bp.route("/inicio")
@login_required
def inicio():
    """Panel de control con el estado real de la base."""
    total_trabajadores = Trabajador.query.filter_by(activo=True).count()
    tarjetas_activas = Tarjeta.query.filter_by(estado="activa").count()
    total_horarios = Horario.query.count()
    lectores_activos = Lector.query.filter_by(estado="activo").count()
    usuarios_activos = Usuario.query.filter_by(activo=True).count()
    total_areas = Area.query.count()

    stats = {
        "trabajadores": total_trabajadores,
        "docentes": Trabajador.query.filter(
            Trabajador.tipo.in_(("docente_tc", "docente_tp"))
        ).count(),
        "administrativos": Trabajador.query.filter_by(tipo="admin").count(),
        "tarjetas": tarjetas_activas,
        "sedes": Sede.query.filter_by(activa=True).count(),
        "areas": total_areas,
        "usuarios": usuarios_activos,
        "lectores": lectores_activos,
    }

    cobertura = [
        {
            "nombre": "Datos maestros",
            "detalle": f"{total_trabajadores} trabajadores · {total_areas} áreas",
            "pct": 100,
        },
        {
            "nombre": "Tarjetas NFC",
            "detalle": f"{tarjetas_activas} de {total_trabajadores} activas",
            "pct": round(tarjetas_activas / total_trabajadores * 100) if total_trabajadores else 0,
        },
        {
            "nombre": "Horarios",
            "detalle": f"{total_horarios:,} turnos · lunes a viernes",
            "pct": round(min(total_horarios / (total_trabajadores * 5), 1) * 100)
            if total_trabajadores
            else 0,
        },
        {
            "nombre": "Lectores",
            "detalle": f"{lectores_activos} activos · 2 sedes",
            "pct": 100,
        },
        {
            "nombre": "Usuarios demo",
            "detalle": f"{usuarios_activos} de 5 roles habilitados",
            "pct": min(round(usuarios_activos / 5 * 100), 100),
        },
        {
            "nombre": "Kiosco NFC",
            "detalle": "Ingresos y salidas · reglas R-01 a R-10",
            "pct": 100,
        },
        {
            "nombre": "Justificaciones",
            "detalle": "Sustento digital y aprobación por área",
            "pct": 100,
        },
        {
            "nombre": "Consolidado",
            "detalle": "Preconsolidado, exportaciones y cierre",
            "pct": 100,
        },
        {
            "nombre": "Panel KPI",
            "detalle": "Tres indicadores, filtros y cinco gráficos",
            "pct": 100,
        },
        {
            "nombre": "Auditoría y administración",
            "detalle": "Trazabilidad y catálogos bajo control",
            "pct": 100,
        },
        {
            "nombre": "Asistencia diaria",
            "detalle": "Tablero por persona, fichas y horarios semanales",
            "pct": 100,
        },
        {
            "nombre": "Línea base histórica",
            "detalle": "2024–2026 con calidad y adopción NFC",
            "pct": 100,
        },
    ]

    actividad = Auditoria.query.order_by(Auditoria.fecha.desc()).limit(6).all()
    inicio_hoy = datetime.combine(datetime.now().date(), time.min)
    marcas_hoy = Marca.query.filter(
        Marca.fecha_hora >= inicio_hoy,
        Marca.fecha_hora < inicio_hoy + timedelta(days=1),
    ).count()
    periodo_anio, periodo_mes = periodo_por_defecto()
    periodo_dashboard = Periodo.query.filter_by(anio=periodo_anio, mes=periodo_mes).first()

    return render_template(
        "main/inicio.html",
        stats=stats,
        cobertura=cobertura,
        actividad=actividad,
        fases=FASES,
        marcas_hoy=marcas_hoy,
        resumen=resumen_justificaciones(current_user),
        periodo_dashboard=periodo_dashboard,
        periodo_anio=periodo_anio,
        periodo_mes=periodo_mes,
        mensaje_rol=MENSAJES_ROL.get(current_user.rol, ""),
        rol_legible=role_label(current_user.rol),
        fases_completadas=sum(1 for _, _, estado in FASES if estado == "completada"),
        hoy_legible=fecha_legible(),
    )
