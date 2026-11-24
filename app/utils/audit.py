"""Registro de auditoría del sistema.

Cada acción sensible deja una fila en la tabla `auditoria` con usuario,
IP, fecha, acción y datos antes/después en formato JSON.
"""

import json
from datetime import datetime
from typing import Any

from flask import has_request_context, request
from flask_login import current_user

from ..extensions import db
from ..models import Auditoria


def _json(valor: Any) -> str | None:
    if valor is None:
        return None
    return json.dumps(valor, ensure_ascii=False, default=str)


def registrar_auditoria(
    accion: str,
    tabla: str | None = None,
    registro_id: int | None = None,
    *,
    datos_anteriores: Any = None,
    datos_nuevos: Any = None,
    id_usuario: int | None = None,
    ip: str | None = None,
    commit: bool = True,
) -> Auditoria:
    """Crea un evento de auditoría y lo persiste.

    Si no se indica id_usuario, se toma el usuario autenticado actual.
    """
    if (
        id_usuario is None
        and has_request_context()
        and current_user
        and current_user.is_authenticated
    ):
        id_usuario = current_user.id_usuario

    if ip is None and has_request_context():
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        if ip and "," in ip:
            ip = ip.split(",")[0].strip()

    evento = Auditoria(
        fecha=datetime.now(),
        accion=accion,
        tabla_afectada=tabla,
        registro_id=registro_id,
        valores_anteriores=_json(datos_anteriores),
        valores_nuevos=_json(datos_nuevos),
        ip=ip,
        id_usuario=id_usuario,
    )
    db.session.add(evento)
    if commit:
        db.session.commit()
    return evento
