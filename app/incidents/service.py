"""Lógica de incidencias, justificaciones y aprobaciones."""

import os
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from flask import current_app
from werkzeug.utils import secure_filename

from ..extensions import db
from ..kiosk import rules
from ..models import Incidencia, Justificacion, Trabajador
from ..utils.audit import registrar_auditoria

EXTENSIONES_PERMITIDAS = {"pdf", "png", "jpg", "jpeg"}
MAX_ARCHIVO_BYTES = 5 * 1024 * 1024
RESUMEN_VACIO = {
    "sin_justificar": 0,
    "en_revision": 0,
    "aprobadas": 0,
    "rechazadas": 0,
}


def area_usuario(usuario):
    """Área del trabajador vinculado al usuario, si existe."""
    return usuario.trabajador.area if usuario.trabajador else None


def en_plazo(incidencia, hoy: date | None = None) -> bool:
    """R-05: cinco días hábiles desde la marcación observada."""
    fecha_evento = (
        incidencia.marca.fecha_hora.date()
        if incidencia.marca is not None
        else incidencia.fecha_creacion.date()
    )
    return rules.justificacion_en_plazo(fecha_evento, hoy or date.today())


def puede_ver(usuario, incidencia) -> bool:
    """Define qué incidencias puede consultar cada rol."""
    if usuario.rol in ("analista", "jefe", "admin"):
        return True
    if usuario.rol == "trabajador":
        return incidencia.id_trabajador == usuario.id_trabajador
    if usuario.rol == "coordinador":
        area = area_usuario(usuario)
        return (
            area is not None
            and incidencia.trabajador is not None
            and incidencia.trabajador.id_area == area.id_area
        )
    return False


def puede_justificar(usuario, incidencia) -> bool:
    """Solo el trabajador dueño, dentro del plazo y sin justificación vigente."""
    if usuario.rol != "trabajador" or incidencia.id_trabajador != usuario.id_trabajador:
        return False
    if incidencia.estado in {"justificada", "cerrada"}:
        return False

    justificacion = incidencia.justificacion
    if justificacion is not None and justificacion.estado in {"enviada", "aprobada"}:
        return False
    return en_plazo(incidencia)


def puede_resolver(usuario, incidencia) -> bool:
    """R-06: el coordinador solo resuelve justificaciones de su área."""
    if usuario.rol != "coordinador":
        return False
    area = area_usuario(usuario)
    if area is None or incidencia.trabajador is None:
        return False
    if incidencia.trabajador.id_area != area.id_area:
        return False
    if incidencia.estado == "cerrada":
        return False
    justificacion = incidencia.justificacion
    return justificacion is not None and justificacion.estado == "enviada"


def _base_resumen(usuario):
    consulta = Incidencia.query
    if usuario.rol == "trabajador":
        return consulta.filter(Incidencia.id_trabajador == usuario.id_trabajador)
    if usuario.rol == "coordinador":
        area = area_usuario(usuario)
        if area is None:
            return None
        return consulta.join(
            Trabajador, Incidencia.id_trabajador == Trabajador.id_trabajador
        ).filter(Trabajador.id_area == area.id_area)
    return consulta


def resumen_justificaciones(usuario) -> dict:
    """Contadores que alimentan el panel y las bandejas."""
    base = _base_resumen(usuario)
    if base is None:
        return dict(RESUMEN_VACIO)

    sin_justificar = (
        base.outerjoin(Justificacion, Justificacion.id_incidencia == Incidencia.id_incidencia)
        .filter(
            Incidencia.estado == "pendiente",
            Justificacion.id_justificacion.is_(None),
        )
        .count()
    )
    en_revision = (
        base.join(Justificacion, Justificacion.id_incidencia == Incidencia.id_incidencia)
        .filter(Justificacion.estado == "enviada")
        .count()
    )
    aprobadas = (
        base.join(Justificacion, Justificacion.id_incidencia == Incidencia.id_incidencia)
        .filter(Justificacion.estado == "aprobada")
        .count()
    )
    rechazadas = (
        base.join(Justificacion, Justificacion.id_incidencia == Incidencia.id_incidencia)
        .filter(Justificacion.estado == "rechazada")
        .count()
    )
    return {
        "sin_justificar": sin_justificar,
        "en_revision": en_revision,
        "aprobadas": aprobadas,
        "rechazadas": rechazadas,
    }


def _guardar_archivo(incidencia, archivo) -> tuple[str, str]:
    """Guarda el sustento y devuelve (nombre almacenado, nombre original)."""
    nombre_original = Path(archivo.filename).name
    extension = nombre_original.rsplit(".", 1)[-1].lower() if "." in nombre_original else ""
    if extension not in EXTENSIONES_PERMITIDAS:
        raise ValueError("El sustento debe ser PDF, PNG, JPG o JPEG.")

    archivo.stream.seek(0, os.SEEK_END)
    tamano = archivo.stream.tell()
    archivo.stream.seek(0)
    if tamano > MAX_ARCHIVO_BYTES:
        raise ValueError("El archivo supera el límite de 5 MB.")

    nombre_seguro = secure_filename(nombre_original) or f"sustento.{extension}"
    almacenado = f"inc{incidencia.id_incidencia}_{uuid4().hex[:10]}_{nombre_seguro}"
    carpeta = Path(current_app.config["UPLOAD_FOLDER"])
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo.save(carpeta / almacenado)
    return almacenado, nombre_original


def registrar_justificacion(incidencia, usuario, motivo: str, archivo):
    """Crea o reenvía la justificación de una incidencia propia."""
    if not puede_ver(usuario, incidencia):
        return False, "No tienes permiso para justificar esta incidencia.", None
    if not puede_justificar(usuario, incidencia):
        if not en_plazo(incidencia):
            return False, "El plazo de cinco días hábiles para justificar venció.", None
        return False, "Esta incidencia ya no requiere una nueva justificación.", None

    motivo = (motivo or "").strip()
    if len(motivo) < 10:
        return False, "Describe el motivo con al menos 10 caracteres.", None

    existente = incidencia.justificacion
    if existente is not None and existente.estado in {"enviada", "aprobada"}:
        return False, "La justificación ya está en revisión o fue aprobada.", None

    archivo_nuevo = bool(archivo is not None and archivo.filename)
    if not archivo_nuevo and (existente is None or not existente.archivo):
        return False, "Adjunta un sustento digital en PDF, PNG o JPG.", None

    almacenado = None
    original = None
    archivo_anterior = existente.archivo if existente is not None else None
    if archivo_nuevo:
        try:
            almacenado, original = _guardar_archivo(incidencia, archivo)
        except (OSError, ValueError) as error:
            return False, str(error), None

    justificacion = existente or Justificacion(incidencia=incidencia)
    justificacion.motivo = motivo
    justificacion.estado = "enviada"
    justificacion.fecha_envio = datetime.now()
    justificacion.fecha_resolucion = None
    justificacion.comentario_resolucion = None
    justificacion.id_usuario_resolvio = None
    if archivo_nuevo:
        justificacion.archivo = almacenado
        justificacion.archivo_original = original
    incidencia.estado = "pendiente"
    db.session.add(justificacion)

    try:
        db.session.commit()
    except Exception:  # pragma: no cover - defensa ante fallos de base
        db.session.rollback()
        if almacenado:
            (Path(current_app.config["UPLOAD_FOLDER"]) / almacenado).unlink(missing_ok=True)
        current_app.logger.exception("No se pudo guardar la justificación.")
        return False, "No se pudo guardar la justificación. Intenta nuevamente.", None

    if archivo_nuevo and archivo_anterior and archivo_anterior != almacenado:
        (Path(current_app.config["UPLOAD_FOLDER"]) / archivo_anterior).unlink(missing_ok=True)

    try:
        registrar_auditoria(
            "JUSTIFICACION_ENVIADA",
            "justificacion",
            justificacion.id_justificacion,
            datos_nuevos={
                "id_incidencia": incidencia.id_incidencia,
                "estado": "enviada",
                "archivo": justificacion.nombre_archivo,
            },
            id_usuario=usuario.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar la justificación.")

    return True, "Justificación enviada. Queda en revisión de tu coordinador.", justificacion


def resolver_justificacion(incidencia, usuario, decision: str, comentario: str):
    """Aprueba o rechaza una justificación de la propia área."""
    if not puede_ver(usuario, incidencia):
        return False, "No tienes permiso para revisar esta incidencia.", None
    if not puede_resolver(usuario, incidencia):
        return False, "La justificación ya no está pendiente de revisión.", None
    if decision not in {"aprobar", "rechazar"}:
        return False, "Selecciona aprobar o rechazar.", None

    comentario = (comentario or "").strip()
    if decision == "rechazar" and not comentario:
        return False, "Indica el motivo del rechazo.", None

    justificacion = incidencia.justificacion
    estado_anterior = justificacion.estado
    aprobada = decision == "aprobar"
    justificacion.estado = "aprobada" if aprobada else "rechazada"
    justificacion.fecha_resolucion = datetime.now()
    justificacion.comentario_resolucion = comentario or None
    justificacion.id_usuario_resolvio = usuario.id_usuario
    incidencia.estado = "justificada" if aprobada else "rechazada"

    try:
        db.session.commit()
    except Exception:  # pragma: no cover
        db.session.rollback()
        current_app.logger.exception("No se pudo resolver la justificación.")
        return False, "No se pudo guardar la decisión. Intenta nuevamente.", None

    accion = "JUSTIFICACION_APROBADA" if aprobada else "JUSTIFICACION_RECHAZADA"
    try:
        registrar_auditoria(
            accion,
            "justificacion",
            justificacion.id_justificacion,
            datos_anteriores={"estado": estado_anterior},
            datos_nuevos={
                "estado": justificacion.estado,
                "id_incidencia": incidencia.id_incidencia,
                "comentario": justificacion.comentario_resolucion,
            },
            id_usuario=usuario.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar la resolución.")

    mensaje = (
        "Justificación aprobada. La incidencia queda justificada."
        if aprobada
        else "Justificación rechazada. El trabajador podrá reenviarla si el plazo lo permite."
    )
    return True, mensaje, justificacion
