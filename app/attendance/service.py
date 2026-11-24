"""Consultas de asistencia diaria, personal y calendarios."""

import calendar
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from math import ceil

from sqlalchemy import or_
from sqlalchemy.orm import joinedload, selectinload

from ..extensions import db
from ..kiosk.rules import TOLERANCIA_ENTRADA_MIN, periodo_bloqueado
from ..models import MESES_LARGOS, Area, Horario, Marca, Periodo, Sede, Trabajador
from ..reports.service import calcular_horas_marcas
from ..utils.audit import registrar_auditoria
from ..utils.helpers import tipo_incidencia_label, tipo_marca_label

TIPOS_PERSONAL = (
    ("admin", "Administrativo"),
    ("docente_tc", "Docente TC"),
    ("docente_tp", "Docente TP"),
)
TIPOS_PERSONAL_LABEL = dict(TIPOS_PERSONAL)
DIAS_LARGOS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
TOLERANCIA_SALIDA_MIN = TOLERANCIA_ENTRADA_MIN

ESTADO_PRESENTE = {
    "Presente",
    "Tardanza",
    "Salida anticipada",
    "Salida pendiente",
    "Presente sin horario",
}


def parse_fecha(valor: str | None, por_defecto: date | None = None) -> date:
    por_defecto = por_defecto or date.today()
    if not valor:
        return por_defecto
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return por_defecto


def rango_dia(fecha: date) -> tuple[datetime, datetime]:
    inicio = datetime.combine(fecha, time.min)
    return inicio, inicio + timedelta(days=1)


def opciones_filtros() -> dict:
    return {
        "sedes": Sede.query.filter_by(activa=True).order_by(Sede.nombre).all(),
        "areas": Area.query.order_by(Area.nombre).all(),
        "tipos": TIPOS_PERSONAL,
    }


def scope_area(usuario):
    """El coordinador solo opera sobre su propia área."""
    if usuario.rol == "coordinador" and usuario.trabajador:
        return usuario.trabajador.area
    return None


def puede_ver_trabajador(usuario, trabajador: Trabajador) -> bool:
    if usuario.rol in {"admin", "analista", "jefe"}:
        return True
    if usuario.rol == "trabajador":
        return bool(
            usuario.trabajador and usuario.trabajador.id_trabajador == trabajador.id_trabajador
        )
    if usuario.rol == "coordinador":
        return bool(usuario.trabajador and usuario.trabajador.id_area == trabajador.id_area)
    return False


def _horario_texto(horario: Horario | None) -> str:
    if horario is None:
        return "Sin horario"
    return f"{horario.hora_entrada:%H:%M}–{horario.hora_salida:%H:%M}"


def _horario_detalle(horario: Horario | None) -> dict:
    if horario is None:
        return {"texto": "Sin horario", "turno": "—"}
    return {
        "texto": _horario_texto(horario),
        "turno": horario.tipo_turno.capitalize(),
    }


def _estado_dia(horario: Horario | None, marcas: list[Marca], fecha: date, hoy: date) -> dict:
    if not marcas:
        if fecha.weekday() >= 5:
            return {"label": "Descanso", "badge": "muted"}
        if horario is None:
            return {"label": "Sin horario", "badge": "muted"}
        if fecha > hoy:
            return {"label": "Programado", "badge": "muted"}
        return {"label": "Falta", "badge": "clay"}

    entradas = [marca for marca in marcas if marca.tipo == "ingreso"]
    salidas = [marca for marca in marcas if marca.tipo == "salida"]

    if not entradas:
        return {"label": "Falta entrada", "badge": "clay"}
    if not salidas:
        return {"label": "Salida pendiente", "badge": "brass"}

    if horario is None:
        return {"label": "Presente sin horario", "badge": "brass"}

    entrada_programada = datetime.combine(fecha, horario.hora_entrada)
    salida_programada = datetime.combine(fecha, horario.hora_salida)
    if salida_programada <= entrada_programada:
        salida_programada += timedelta(days=1)

    if entradas[0].fecha_hora > entrada_programada + timedelta(minutes=TOLERANCIA_ENTRADA_MIN):
        return {"label": "Tardanza", "badge": "brass"}
    if salidas[-1].fecha_hora < salida_programada - timedelta(minutes=TOLERANCIA_SALIDA_MIN):
        return {"label": "Salida anticipada", "badge": "brass"}
    return {"label": "Presente", "badge": "jade"}


def _incidencias_de_marcas(marcas: list[Marca]) -> list[dict]:
    resultado = []
    for marca in marcas:
        incidencia = getattr(marca, "incidencia", None)
        if incidencia is None:
            continue
        resultado.append(
            {
                "id": incidencia.id_incidencia,
                "tipo": incidencia.tipo,
                "tipo_label": tipo_incidencia_label(incidencia.tipo),
                "estado": incidencia.estado,
            }
        )
    return resultado


def _fila_trabajador(
    trabajador: Trabajador,
    horario: Horario | None,
    marcas: list[Marca],
    fecha: date,
    hoy: date,
) -> dict:
    entradas = [marca for marca in marcas if marca.tipo == "ingreso"]
    salidas = [marca for marca in marcas if marca.tipo == "salida"]
    estado = _estado_dia(horario, marcas, fecha, hoy)
    incidencias = _incidencias_de_marcas(marcas)
    return {
        "trabajador": trabajador,
        "nombre_corto": trabajador.nombre_corto,
        "area": trabajador.area.nombre,
        "tipo": TIPOS_PERSONAL_LABEL.get(trabajador.tipo, trabajador.tipo),
        "horario": _horario_texto(horario),
        "entrada": entradas[0].fecha_hora.strftime("%H:%M") if entradas else "—",
        "salida": salidas[-1].fecha_hora.strftime("%H:%M") if salidas else "—",
        "horas": calcular_horas_marcas(marcas),
        "estado": estado,
        "incidencias": incidencias,
        "total_incidencias": len(incidencias),
    }


def resumen_dia(
    fecha: date,
    usuario,
    sede_id: int | None = None,
    area_id: int | None = None,
    tipo: str | None = None,
    q: str = "",
    pagina: int = 1,
    por_pagina: int = 25,
) -> dict:
    area_scope = scope_area(usuario)
    if area_scope is not None:
        area_id = area_scope.id_area

    consulta = (
        Trabajador.query.options(
            joinedload(Trabajador.area),
            selectinload(Trabajador.tarjeta),
        )
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Trabajador.activo.is_(True))
    )
    if sede_id:
        consulta = consulta.filter(Area.id_sede == sede_id)
    if area_id:
        consulta = consulta.filter(Trabajador.id_area == area_id)
    if tipo:
        consulta = consulta.filter(Trabajador.tipo == tipo)
    if q:
        consulta = consulta.filter(
            or_(Trabajador.nombres.ilike(f"%{q}%"), Trabajador.dni.ilike(f"%{q}%"))
        )
    trabajadores = consulta.order_by(Trabajador.nombres).all()

    ids = [trabajador.id_trabajador for trabajador in trabajadores]
    horarios = {}
    marcas_por_trabajador: dict[int, list[Marca]] = defaultdict(list)
    if ids:
        for horario in Horario.query.filter(
            Horario.dia_semana == fecha.weekday(), Horario.id_trabajador.in_(ids)
        ):
            horarios[horario.id_trabajador] = horario
        inicio, fin = rango_dia(fecha)
        marcas = (
            Marca.query.options(joinedload(Marca.incidencia))
            .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
            .filter(Marca.id_trabajador.in_(ids))
            .order_by(Marca.fecha_hora)
            .all()
        )
        for marca in marcas:
            marcas_por_trabajador[marca.id_trabajador].append(marca)

    hoy = date.today()
    filas = [
        _fila_trabajador(
            trabajador,
            horarios.get(trabajador.id_trabajador),
            marcas_por_trabajador.get(trabajador.id_trabajador, []),
            fecha,
            hoy,
        )
        for trabajador in trabajadores
    ]

    resumen = {
        "programados": sum(1 for fila in filas if fila["horario"] != "Sin horario"),
        "presentes": sum(1 for fila in filas if fila["estado"]["label"] in ESTADO_PRESENTE),
        "tardanzas": sum(1 for fila in filas if fila["estado"]["label"] == "Tardanza"),
        "faltas": sum(1 for fila in filas if fila["estado"]["label"] == "Falta"),
        "pendientes": sum(
            1 for fila in filas if fila["estado"]["label"] in {"Salida pendiente", "Falta entrada"}
        ),
        "incidencias": sum(fila["total_incidencias"] for fila in filas),
        "sin_horario": sum(1 for fila in filas if fila["horario"] == "Sin horario"),
    }

    total = len(filas)
    paginas = max(1, ceil(total / por_pagina))
    pagina = min(max(1, pagina), paginas)
    desde = (pagina - 1) * por_pagina
    hasta = min(desde + por_pagina, total)
    return {
        "filas": filas[desde:hasta],
        "total": total,
        "pagina": pagina,
        "paginas": paginas,
        "desde": desde + 1 if total else 0,
        "hasta": hasta,
        "por_pagina": por_pagina,
        "resumen": resumen,
        "fecha": fecha,
        "etiqueta_fecha": f"{DIAS_LARGOS[fecha.weekday()]} {fecha:%d/%m/%Y}",
        "area_scope": area_scope,
    }


def _resumen_horario(trabajador: Trabajador) -> dict:
    horarios = sorted(trabajador.horarios, key=lambda horario: horario.dia_semana)
    if not horarios:
        return {"texto": "Sin horario", "dias": 0, "patron": "—"}
    dias = sorted({horario.dia_semana for horario in horarios})
    patrones = {(horario.hora_entrada, horario.hora_salida) for horario in horarios}
    if len(patrones) == 1:
        entrada, salida = next(iter(patrones))
        rango_dias = "L–V" if dias == [0, 1, 2, 3, 4] else f"{len(dias)} días"
        return {
            "texto": f"{rango_dias} · {entrada:%H:%M}–{salida:%H:%M}",
            "dias": len(dias),
            "patron": f"{entrada:%H:%M}–{salida:%H:%M}",
        }
    return {
        "texto": f"{len(dias)} días · horario variable",
        "dias": len(dias),
        "patron": "Variable",
    }


def listar_personal(
    usuario,
    q: str = "",
    area_id: int | None = None,
    tipo: str | None = None,
    estado: str = "activos",
    pagina: int = 1,
    por_pagina: int = 15,
) -> dict:
    area_scope = scope_area(usuario)
    if area_scope is not None:
        area_id = area_scope.id_area

    consulta = Trabajador.query.options(
        joinedload(Trabajador.area),
        selectinload(Trabajador.tarjeta),
        selectinload(Trabajador.horarios),
    ).join(Area, Trabajador.id_area == Area.id_area)
    if area_id:
        consulta = consulta.filter(Trabajador.id_area == area_id)
    if tipo:
        consulta = consulta.filter(Trabajador.tipo == tipo)
    if estado == "activos":
        consulta = consulta.filter(Trabajador.activo.is_(True))
    elif estado == "inactivos":
        consulta = consulta.filter(Trabajador.activo.is_(False))
    if q:
        consulta = consulta.filter(
            or_(
                Trabajador.nombres.ilike(f"%{q}%"),
                Trabajador.dni.ilike(f"%{q}%"),
                Trabajador.cargo.ilike(f"%{q}%"),
            )
        )
    paginacion = consulta.order_by(Trabajador.nombres).paginate(
        page=max(1, pagina), per_page=por_pagina, error_out=False
    )
    filas = []
    for trabajador in paginacion.items:
        filas.append(
            {
                "trabajador": trabajador,
                "nombre_corto": trabajador.nombre_corto,
                "area": trabajador.area.nombre,
                "tipo": TIPOS_PERSONAL_LABEL.get(trabajador.tipo, trabajador.tipo),
                "horario": _resumen_horario(trabajador),
                "tarjeta": trabajador.tarjeta,
            }
        )
    return {
        "filas": filas,
        "paginacion": paginacion,
        "total": paginacion.total,
        "area_scope": area_scope,
    }


def _semana_trabajador(trabajador: Trabajador) -> list[dict]:
    horarios = {horario.dia_semana: horario for horario in trabajador.horarios}
    semana = []
    for dia in range(7):
        horario = horarios.get(dia)
        semana.append(
            {
                "dia": dia,
                "nombre": DIAS_LARGOS[dia],
                "laborable": horario is not None,
                "horario": _horario_detalle(horario),
            }
        )
    return semana


def _ficha_mes(trabajador: Trabajador, anio: int, mes: int, hoy: date) -> dict:
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    inicio = datetime(anio, mes, 1)
    if mes == 12:
        fin = datetime(anio + 1, 1, 1)
    else:
        fin = datetime(anio, mes + 1, 1)

    marcas = (
        Marca.query.options(joinedload(Marca.incidencia))
        .filter(
            Marca.id_trabajador == trabajador.id_trabajador,
            Marca.fecha_hora >= inicio,
            Marca.fecha_hora < fin,
        )
        .order_by(Marca.fecha_hora)
        .all()
    )
    por_dia: dict[date, list[Marca]] = defaultdict(list)
    for marca in marcas:
        por_dia[marca.fecha_hora.date()].append(marca)

    horarios = {horario.dia_semana: horario for horario in trabajador.horarios}
    dias = []
    total_horas = 0.0
    for numero in range(1, ultimo_dia + 1):
        fecha = date(anio, mes, numero)
        horario = horarios.get(fecha.weekday())
        marcas_dia = por_dia.get(fecha, [])
        estado = _estado_dia(horario, marcas_dia, fecha, hoy)
        horas = calcular_horas_marcas(marcas_dia)
        total_horas += horas
        dias.append(
            {
                "fecha": fecha,
                "numero": numero,
                "dia_semana": fecha.weekday(),
                "horario": _horario_detalle(horario),
                "marcas": marcas_dia,
                "entrada": next(
                    (m.fecha_hora.strftime("%H:%M") for m in marcas_dia if m.tipo == "ingreso"),
                    "—",
                ),
                "salida": next(
                    (
                        m.fecha_hora.strftime("%H:%M")
                        for m in reversed(marcas_dia)
                        if m.tipo == "salida"
                    ),
                    "—",
                ),
                "horas": horas,
                "estado": estado,
                "incidencias": _incidencias_de_marcas(marcas_dia),
                "es_hoy": fecha == hoy,
                "es_futuro": fecha > hoy,
            }
        )

    semanas = []
    for semana in calendar.Calendar(firstweekday=0).monthdayscalendar(anio, mes):
        semanas.append([dias[numero - 1] if numero else None for numero in semana])

    incidentes = [
        {
            "id": incidencia["id"],
            "fecha": dia["fecha"],
            "tipo": incidencia["tipo_label"],
            "estado": incidencia["estado"],
        }
        for dia in dias
        for incidencia in dia["incidencias"]
    ]
    incidentes.sort(key=lambda item: item["fecha"], reverse=True)

    return {
        "anio": anio,
        "mes": mes,
        "mes_label": f"{MESES_LARGOS[mes - 1]} {anio}",
        "dias": dias,
        "semanas": semanas,
        "total_horas": round(total_horas, 2),
        "dias_con_marcas": sum(1 for dia in dias if dia["marcas"]),
        "tardanzas": sum(1 for dia in dias if dia["estado"]["label"] == "Tardanza"),
        "faltas": sum(1 for dia in dias if dia["estado"]["label"] == "Falta"),
        "incidentes": incidentes[:6],
        "total_incidentes": len(incidentes),
        "scheduled_days": sum(1 for dia in dias if dia["horario"]["texto"] != "Sin horario"),
    }


def ficha_trabajador(trabajador: Trabajador, anio: int, mes: int) -> dict:
    hoy = date.today()
    mes = max(1, min(12, mes))
    datos_mes = _ficha_mes(trabajador, anio, mes, hoy)
    anterior_anio, anterior_mes = (anio - 1, 12) if mes == 1 else (anio, mes - 1)
    siguiente_anio, siguiente_mes = (anio + 1, 1) if mes == 12 else (anio, mes + 1)
    return {
        "trabajador": trabajador,
        "tipo_label": TIPOS_PERSONAL_LABEL.get(trabajador.tipo, trabajador.tipo),
        "semana": _semana_trabajador(trabajador),
        "mes": datos_mes,
        "anterior": (anterior_anio, anterior_mes),
        "siguiente": (siguiente_anio, siguiente_mes),
    }


# ---------------------------------------------------------------------------
# Corrección manual de marcaciones (Fase 8)
# ---------------------------------------------------------------------------
MEDIOS_ETIQUETA = {"nfc": "NFC", "huella": "Huella", "contingencia": "Contingencia"}
ESTADOS_MARCA_LABEL = {"valida": "Válida", "observada": "Observada"}
MOTIVO_MINIMO = 8


def _rango_mes(anio: int, mes: int) -> tuple[datetime, datetime]:
    inicio = datetime(anio, mes, 1)
    fin = datetime(anio + 1, 1, 1) if mes == 12 else datetime(anio, mes + 1, 1)
    return inicio, fin


def estado_mes_periodo(anio: int, mes: int) -> dict:
    """Indica si el mes tiene un periodo cerrado que impide corregir marcas."""
    periodo = Periodo.query.filter_by(anio=anio, mes=mes).first()
    if periodo is None:
        return {"estado": "sin periodo", "bloqueado": False}
    return {"estado": periodo.estado, "bloqueado": periodo_bloqueado(periodo.estado)}


def listar_marcas_mes(trabajador: Trabajador, anio: int, mes: int) -> dict:
    """Lista las marcaciones del mes con su sede, lector e incidencia."""
    inicio, fin = _rango_mes(anio, mes)
    marcas = (
        Marca.query.options(
            joinedload(Marca.sede),
            joinedload(Marca.lector),
            joinedload(Marca.incidencia),
        )
        .filter(
            Marca.id_trabajador == trabajador.id_trabajador,
            Marca.fecha_hora >= inicio,
            Marca.fecha_hora < fin,
        )
        .order_by(Marca.fecha_hora)
        .all()
    )
    filas = []
    for marca in marcas:
        incidencia = marca.incidencia
        filas.append(
            {
                "id": marca.id_marca,
                "fecha": marca.fecha_hora.date(),
                "hora": marca.fecha_hora.strftime("%H:%M"),
                "fecha_hora": marca.fecha_hora,
                "tipo": marca.tipo,
                "tipo_label": tipo_marca_label(marca.tipo),
                "medio": marca.medio,
                "medio_label": MEDIOS_ETIQUETA.get(marca.medio, marca.medio),
                "estado": marca.estado,
                "estado_label": ESTADOS_MARCA_LABEL.get(marca.estado, marca.estado),
                "sede": marca.sede.nombre if marca.sede else "—",
                "lector": marca.lector.nombre if marca.lector else "—",
                "incidencia": (
                    {
                        "id": incidencia.id_incidencia,
                        "tipo_label": tipo_incidencia_label(incidencia.tipo),
                        "estado": incidencia.estado,
                    }
                    if incidencia
                    else None
                ),
            }
        )
    return {
        "trabajador": trabajador,
        "anio": anio,
        "mes": mes,
        "mes_label": f"{MESES_LARGOS[mes - 1]} {anio}",
        "marcas": filas,
        "total": len(filas),
        "periodo": estado_mes_periodo(anio, mes),
        "anterior": (anio - 1, 12) if mes == 1 else (anio, mes - 1),
        "siguiente": (anio + 1, 1) if mes == 12 else (anio, mes + 1),
    }


def corregir_marca(
    marca: Marca,
    usuario,
    fecha: date,
    hora: time,
    tipo: str,
    motivo: str,
) -> tuple[bool, str]:
    """Corrige la fecha, la hora o el tipo de una marcación y lo audita."""
    motivo = (motivo or "").strip()
    if len(motivo) < MOTIVO_MINIMO:
        return False, f"Escribe un motivo de al menos {MOTIVO_MINIMO} caracteres."
    if tipo not in {"ingreso", "salida"}:
        return False, "El tipo de marcación no es válido."

    nuevo_momento = datetime.combine(fecha, hora)
    if nuevo_momento == marca.fecha_hora and tipo == marca.tipo:
        return False, "La corrección no cambia la marcación."

    meses = {
        (marca.fecha_hora.year, marca.fecha_hora.month),
        (nuevo_momento.year, nuevo_momento.month),
    }
    for anio, mes in sorted(meses):
        estado = estado_mes_periodo(anio, mes)
        if estado["bloqueado"]:
            return False, (
                f"El periodo de {MESES_LARGOS[mes - 1]} {anio} está "
                f"{estado['estado']} y no admite correcciones."
            )

    anterior = {
        "fecha_hora": marca.fecha_hora.isoformat(timespec="minutes"),
        "tipo": marca.tipo,
        "estado": marca.estado,
    }
    incidencia = marca.incidencia
    incidencia_anterior = None
    if incidencia is not None and incidencia.estado in {"pendiente", "rechazada"}:
        incidencia_anterior = incidencia.estado
        anterior["incidencia"] = incidencia_anterior
        incidencia.estado = "cerrada"
        nota = f"Corrección manual: {motivo}"
        observacion = (incidencia.observacion or "").strip()
        incidencia.observacion = f"{observacion} {nota}".strip()[:300]

    marca.fecha_hora = nuevo_momento
    marca.tipo = tipo
    marca.estado = "valida"

    try:
        db.session.commit()
    except Exception:  # pragma: no cover
        db.session.rollback()
        return False, "No se pudo guardar la corrección."

    registrar_auditoria(
        "CORREGIR_MARCA",
        "marca",
        marca.id_marca,
        datos_anteriores=anterior,
        datos_nuevos={
            "fecha_hora": nuevo_momento.isoformat(timespec="minutes"),
            "tipo": tipo,
            "estado": marca.estado,
            "motivo": motivo,
            **({"incidencia": "cerrada"} if incidencia_anterior else {}),
        },
        id_usuario=usuario.id_usuario,
    )
    return True, "Marcación corregida y registrada en auditoría."
