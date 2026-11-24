"""Servicio de marcación del kiosco.

Compone las reglas R-01 a R-10 con la base de datos: valida la tarjeta y el
lector, resuelve la secuencia del día, crea la marca y la incidencia cuando
corresponde, y deja constancia en auditoría.
"""

from datetime import datetime, time

from flask import current_app

from ..extensions import db
from ..models import Horario, Incidencia, Lector, Marca, Tarjeta
from ..utils.audit import registrar_auditoria
from . import rules

TIPO_LABEL = {"ingreso": "Ingreso", "salida": "Salida"}
TIPO_LECTOR = {"ingreso": "entrada", "salida": "salida"}
INCIDENCIA_LABEL = {
    "falta_entrada": "Falta de entrada",
    "falta_salida": "Falta de salida",
    "fuera_horario": "Fuera de horario",
    "duplicado": "Duplicado",
    "doble_sede": "Doble sede",
}


def _resultado(
    ok: bool,
    estado: str,
    titulo: str,
    mensaje: str,
    *,
    trabajador: str | None = None,
    area: str | None = None,
    tipo: str | None = None,
    hora: str | None = None,
    fecha: str | None = None,
    sede: str | None = None,
    lector: str | None = None,
    incidencia: str | None = None,
    incidencia_label: str | None = None,
    id_marca: int | None = None,
) -> dict:
    return {
        "ok": ok,
        "estado": estado,
        "titulo": titulo,
        "mensaje": mensaje,
        "trabajador": trabajador,
        "area": area,
        "tipo": tipo,
        "hora": hora,
        "fecha": fecha,
        "sede": sede,
        "lector": lector,
        "incidencia": incidencia,
        "incidencia_label": incidencia_label,
        "id_marca": id_marca,
    }


def _auditar(
    accion: str,
    *,
    uid: str,
    tipo: str,
    id_lector: int | None,
    estado: str,
    trabajador=None,
    sede=None,
    incidencia: str | None = None,
    id_marca: int | None = None,
    referencia: int | None = None,
) -> None:
    datos = {
        "uid": uid,
        "tipo": tipo,
        "id_lector": id_lector,
        "estado": estado,
        "incidencia": incidencia,
    }
    if trabajador is not None:
        datos["id_trabajador"] = trabajador.id_trabajador
        datos["trabajador"] = trabajador.nombre_corto
    if sede is not None:
        datos["id_sede"] = sede.id_sede
        datos["sede"] = sede.nombre
    if referencia is not None:
        datos["marca_referencia"] = referencia
    try:
        registrar_auditoria(accion, "marca", id_marca, datos_nuevos=datos)
    except Exception:  # pragma: no cover - defensa ante fallos de auditoría
        current_app.logger.exception("No se pudo registrar la auditoría de la marcación.")


def _error(
    codigo: str,
    mensaje: str,
    *,
    uid: str,
    tipo: str | None,
    id_lector: int | None,
    trabajador=None,
    sede=None,
) -> dict:
    _auditar(
        "MARCA_RECHAZADA",
        uid=uid,
        tipo=tipo or "",
        id_lector=id_lector,
        estado=codigo,
        trabajador=trabajador,
        sede=sede,
    )
    return _resultado(
        False,
        "error",
        "No se pudo registrar",
        mensaje,
        trabajador=trabajador.nombre_corto if trabajador is not None else None,
        area=trabajador.area.nombre if trabajador is not None else None,
        tipo=TIPO_LABEL.get(tipo or ""),
        sede=sede.nombre if sede is not None else None,
    )


def registrar_marcacion(
    uid: str | None,
    tipo: str | None,
    id_lector: int | None,
    ahora: datetime | None = None,
) -> dict:
    """Registra una marcación y devuelve un resultado serializable."""
    uid = (uid or "").strip().upper()
    tipo = (tipo or "").strip().lower()
    try:
        id_lector = int(id_lector) if id_lector is not None else None
    except (TypeError, ValueError):
        id_lector = None

    if not uid:
        return _error(
            "UID_REQUERIDO",
            "Acerca una tarjeta o escribe su UID.",
            uid=uid,
            tipo=tipo,
            id_lector=id_lector,
        )
    if tipo not in TIPO_LABEL:
        return _error(
            "TIPO_INVALIDO", "Selecciona ingreso o salida.", uid=uid, tipo=tipo, id_lector=id_lector
        )
    if not id_lector:
        return _error(
            "LECTOR_REQUERIDO", "Selecciona un lector.", uid=uid, tipo=tipo, id_lector=id_lector
        )

    if ahora is None:
        ahora = datetime.now()
    elif ahora.tzinfo is not None:
        ahora = ahora.replace(tzinfo=None)

    tarjeta = Tarjeta.query.filter_by(uid=uid).first()
    validacion = rules.validar_tarjeta(tarjeta)
    if not validacion.ok:
        return _error(
            validacion.codigo, validacion.mensaje, uid=uid, tipo=tipo, id_lector=id_lector
        )

    trabajador = tarjeta.trabajador
    lector = db.session.get(Lector, id_lector)
    if lector is None or lector.estado != "activo":
        return _error(
            "LECTOR_INVALIDO",
            "El lector no existe o está fuera de servicio.",
            uid=uid,
            tipo=tipo,
            id_lector=id_lector,
            trabajador=trabajador,
        )
    tipo_lector_esperado = TIPO_LECTOR[tipo]
    if lector.tipo != tipo_lector_esperado:
        return _error(
            "LECTOR_INCOMPATIBLE",
            f"El lector seleccionado es de {lector.tipo}; elige uno de {tipo_lector_esperado}.",
            uid=uid,
            tipo=tipo,
            id_lector=id_lector,
            trabajador=trabajador,
            sede=lector.sede,
        )

    inicio_dia = datetime.combine(ahora.date(), time.min)
    ultima_marca = (
        Marca.query.filter(
            Marca.id_trabajador == trabajador.id_trabajador,
            Marca.fecha_hora >= inicio_dia,
            Marca.fecha_hora <= ahora,
        )
        .order_by(Marca.fecha_hora.desc(), Marca.id_marca.desc())
        .first()
    )

    if rules.es_duplicado(ultima_marca, tipo, ahora):
        _auditar(
            "MARCA_DUPLICADA",
            uid=uid,
            tipo=tipo,
            id_lector=id_lector,
            estado="duplicado",
            trabajador=trabajador,
            sede=lector.sede,
            referencia=ultima_marca.id_marca if ultima_marca else None,
        )
        return _resultado(
            False,
            "duplicado",
            "Marcación duplicada",
            "Ya se registró esta marcación hace menos de 2 minutos. Se ignoró el intento.",
            trabajador=trabajador.nombre_corto,
            area=trabajador.area.nombre,
            tipo=TIPO_LABEL[tipo],
            hora=ahora.strftime("%H:%M"),
            fecha=ahora.strftime("%d/%m/%Y"),
            sede=lector.sede.nombre,
            lector=lector.nombre,
        )

    incidencia_secuencia = rules.incidencia_por_secuencia(ultima_marca, tipo)
    doble_sede = rules.es_doble_sede(ultima_marca, lector.id_sede, ahora)

    tolerancia = None
    if tipo == "ingreso":
        horario = Horario.query.filter_by(
            id_trabajador=trabajador.id_trabajador,
            dia_semana=ahora.weekday(),
        ).first()
        tolerancia = rules.evaluar_tolerancia(horario, ahora)

    motivos: list[tuple[str, str]] = []
    if incidencia_secuencia == "falta_entrada":
        motivos.append(("falta_entrada", "Salida registrada sin un ingreso previo en el día."))
    if doble_sede and ultima_marca is not None:
        motivos.append(
            (
                "doble_sede",
                f"Marcación en otra sede hace menos de 30 minutos ({ultima_marca.sede.nombre}).",
            )
        )
    if tolerancia is not None and not tolerancia.ok:
        motivos.append((tolerancia.incidencia or "fuera_horario", tolerancia.mensaje))

    incidencia_actual = motivos[0][0] if motivos else None
    observacion = " ".join(mensaje for _, mensaje in motivos)
    estado_marca = "observada" if motivos else "valida"

    marca = Marca(
        fecha_hora=ahora,
        tipo=tipo,
        estado=estado_marca,
        medio="nfc",
        id_trabajador=trabajador.id_trabajador,
        id_lector=lector.id_lector,
        id_sede=lector.id_sede,
    )
    db.session.add(marca)

    incidencia_previa_creada = False
    try:
        db.session.flush()
        if incidencia_actual:
            db.session.add(
                Incidencia(
                    tipo=incidencia_actual,
                    estado="pendiente",
                    observacion=observacion,
                    id_marca=marca.id_marca,
                    id_trabajador=trabajador.id_trabajador,
                )
            )
        if (
            incidencia_secuencia == "falta_salida"
            and ultima_marca is not None
            and ultima_marca.incidencia is None
        ):
            db.session.add(
                Incidencia(
                    tipo="falta_salida",
                    estado="pendiente",
                    observacion="Ingreso sin salida registrado; se detectó al marcar un nuevo ingreso.",
                    id_marca=ultima_marca.id_marca,
                    id_trabajador=trabajador.id_trabajador,
                )
            )
            incidencia_previa_creada = True
        db.session.commit()
    except Exception:  # pragma: no cover - defensa ante fallos de base
        db.session.rollback()
        current_app.logger.exception("No se pudo registrar la marcación.")
        return _error(
            "ERROR_INTERNO",
            "No se pudo guardar la marcación. Intenta nuevamente.",
            uid=uid,
            tipo=tipo,
            id_lector=id_lector,
            trabajador=trabajador,
            sede=lector.sede,
        )

    if motivos:
        titulo = "Marcación observada"
        mensaje = f"{TIPO_LABEL[tipo]} registrado con observación: {observacion}"
    else:
        titulo = f"{TIPO_LABEL[tipo]} registrado"
        mensaje = f"{TIPO_LABEL[tipo]} registrado correctamente."
    if incidencia_previa_creada:
        mensaje += " Se generó una incidencia por la salida faltante del ingreso anterior."

    _auditar(
        f"MARCA_{tipo.upper()}",
        uid=uid,
        tipo=tipo,
        id_lector=id_lector,
        estado=estado_marca,
        trabajador=trabajador,
        sede=lector.sede,
        incidencia=incidencia_actual,
        id_marca=marca.id_marca,
    )

    return _resultado(
        True,
        estado_marca,
        titulo,
        mensaje,
        trabajador=trabajador.nombre_corto,
        area=trabajador.area.nombre,
        tipo=TIPO_LABEL[tipo],
        hora=ahora.strftime("%H:%M"),
        fecha=ahora.strftime("%d/%m/%Y"),
        sede=lector.sede.nombre,
        lector=lector.nombre,
        incidencia=incidencia_actual,
        incidencia_label=INCIDENCIA_LABEL.get(incidencia_actual or ""),
        id_marca=marca.id_marca,
    )
