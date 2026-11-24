"""Consulta y exportación del registro de auditoría."""

import csv
import io
from datetime import datetime, time

from flask import abort, current_app, render_template, request, send_file
from flask_login import current_user

from ..extensions import db
from ..models import Auditoria, Usuario
from ..utils.audit import registrar_auditoria
from ..utils.decorators import roles_required
from . import audit_bp
from .presenter import presentar_evento

ROLES_AUDITORIA = ("analista", "jefe", "admin")


def _filtros() -> dict:
    usuario_id = request.args.get("usuario", type=int)
    tabla = request.args.get("tabla", "").strip()
    accion = request.args.get("accion", "").strip()
    desde_texto = request.args.get("desde", "").strip()
    hasta_texto = request.args.get("hasta", "").strip()

    desde = hasta = None
    if desde_texto:
        try:
            desde = datetime.combine(datetime.strptime(desde_texto, "%Y-%m-%d").date(), time.min)
        except ValueError:
            desde = None
    if hasta_texto:
        try:
            hasta = datetime.combine(datetime.strptime(hasta_texto, "%Y-%m-%d").date(), time.max)
        except ValueError:
            hasta = None

    return {
        "usuario": usuario_id,
        "tabla": tabla,
        "accion": accion,
        "desde": desde,
        "hasta": hasta,
        "desde_texto": desde_texto,
        "hasta_texto": hasta_texto,
    }


def _consulta(filtros: dict):
    consulta = Auditoria.query
    if filtros["usuario"]:
        consulta = consulta.filter(Auditoria.id_usuario == filtros["usuario"])
    if filtros["tabla"]:
        consulta = consulta.filter(Auditoria.tabla_afectada == filtros["tabla"])
    if filtros["accion"]:
        consulta = consulta.filter(Auditoria.accion == filtros["accion"])
    if filtros["desde"]:
        consulta = consulta.filter(Auditoria.fecha >= filtros["desde"])
    if filtros["hasta"]:
        consulta = consulta.filter(Auditoria.fecha <= filtros["hasta"])
    return consulta.order_by(Auditoria.fecha.desc(), Auditoria.id_evento.desc())


def _opciones() -> dict:
    usuarios = Usuario.query.order_by(Usuario.correo).all()
    tablas = [
        fila[0]
        for fila in db.session.query(Auditoria.tabla_afectada)
        .filter(Auditoria.tabla_afectada.isnot(None))
        .distinct()
        .order_by(Auditoria.tabla_afectada)
        .all()
    ]
    acciones = [
        fila[0]
        for fila in db.session.query(Auditoria.accion).distinct().order_by(Auditoria.accion).all()
    ]
    return {"usuarios": usuarios, "tablas": tablas, "acciones": acciones}


@audit_bp.route("/auditoria")
@roles_required(*ROLES_AUDITORIA)
def index():
    filtros = _filtros()
    pagina = request.args.get("pagina", 1, type=int)
    paginacion = _consulta(filtros).paginate(page=pagina, per_page=25, error_out=False)
    query_args = {clave: valor for clave, valor in request.args.items() if clave != "pagina"}
    return render_template(
        "audit/index.html",
        eventos=paginacion.items,
        paginacion=paginacion,
        filtros=filtros,
        opciones=_opciones(),
        query_args=query_args,
    )


@audit_bp.route("/auditoria/<int:evento_id>")
@roles_required(*ROLES_AUDITORIA)
def detalle(evento_id: int):
    evento = db.session.get(Auditoria, evento_id)
    if evento is None:
        abort(404)
    return render_template(
        "audit/detalle.html",
        evento=evento,
        detalle=presentar_evento(evento),
    )


@audit_bp.route("/auditoria/exportar.csv")
@roles_required(*ROLES_AUDITORIA)
def exportar():
    filtros = _filtros()
    eventos = _consulta(filtros).limit(5000).all()
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=",", lineterminator="\n")
    escritor.writerow(["Fecha", "Usuario", "Accion", "Tabla", "Registro", "IP", "Antes", "Despues"])
    for evento in eventos:
        escritor.writerow(
            [
                evento.fecha.strftime("%d/%m/%Y %H:%M:%S"),
                evento.usuario.correo if evento.usuario else "sistema/kiosco",
                evento.accion,
                evento.tabla_afectada or "",
                evento.registro_id or "",
                evento.ip or "",
                evento.valores_anteriores or "",
                evento.valores_nuevos or "",
            ]
        )
    contenido = salida.getvalue().encode("utf-8-sig")

    try:
        registrar_auditoria(
            "EXPORTACION",
            "auditoria",
            None,
            datos_nuevos={"eventos": len(eventos)},
            id_usuario=current_user.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar la exportación de auditoría.")

    return send_file(
        io.BytesIO(contenido),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="auditoria.csv",
    )
