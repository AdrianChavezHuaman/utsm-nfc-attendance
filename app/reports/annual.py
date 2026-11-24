"""Consolidado anual y comparativas enero–enero / año–año."""

import csv
import io
from collections import defaultdict
from datetime import datetime, timedelta

from openpyxl import Workbook
from openpyxl.styles import Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import case, func

from ..dashboard.service import datos_indicadores_anuales
from ..extensions import db
from ..models import MESES_LARGOS, Area, Incidencia, Marca, Periodo, Sede, Trabajador
from ..utils.helpers import estado_periodo

TIPOS_PERSONAL = (
    ("admin", "Administrativo"),
    ("docente_tc", "Docente TC"),
    ("docente_tp", "Docente TP"),
)
MESES = tuple(range(1, 13))
SEMESTRES = {
    "s1": {
        "codigo": "S1",
        "nombre": "Primer semestre",
        "rango": "Enero – junio",
        "meses": tuple(range(1, 7)),
    },
    "s2": {
        "codigo": "S2",
        "nombre": "Segundo semestre",
        "rango": "Julio – diciembre",
        "meses": tuple(range(7, 13)),
    },
}
ANIOS = (2024, 2025, 2026, 2027)
ESTADOS_BADGE = {
    "abierto": "brass",
    "cerrado": "jade",
    "bloqueado": "muted",
    "sin datos": "muted",
    "sin periodo": "muted",
}


def _rango_mes(anio: int, mes: int) -> tuple[datetime, datetime]:
    inicio = datetime(anio, mes, 1)
    fin = datetime(anio + 1, 1, 1) if mes == 12 else datetime(anio, mes + 1, 1)
    return inicio, fin


def _consulta_marcas(
    inicio: datetime,
    fin: datetime,
    sede_id: int | None,
    area_id: int | None,
    tipo: str | None,
):
    consulta = (
        db.session.query(
            Marca.id_trabajador,
            Marca.fecha_hora,
            Marca.tipo,
            Marca.medio,
        )
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        consulta = consulta.filter(Area.id_sede == sede_id)
    if area_id:
        consulta = consulta.filter(Area.id_area == area_id)
    if tipo:
        consulta = consulta.filter(Trabajador.tipo == tipo)
    return consulta.order_by(Marca.fecha_hora)


def _contar_trabajadores(
    anio: int,
    sede_id: int | None,
    area_id: int | None,
    tipo: str | None,
) -> int:
    inicio = datetime(anio, 1, 1)
    fin = datetime(anio + 1, 1, 1)
    consulta = (
        db.session.query(func.count(func.distinct(Marca.id_trabajador)))
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        consulta = consulta.filter(Area.id_sede == sede_id)
    if area_id:
        consulta = consulta.filter(Area.id_area == area_id)
    if tipo:
        consulta = consulta.filter(Trabajador.tipo == tipo)
    return consulta.scalar() or 0


def _consulta_incidencias(
    inicio: datetime,
    fin: datetime,
    sede_id: int | None,
    area_id: int | None,
    tipo: str | None,
) -> int:
    consulta = (
        db.session.query(func.count(Incidencia.id_incidencia))
        .join(Marca, Incidencia.id_marca == Marca.id_marca)
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        consulta = consulta.filter(Area.id_sede == sede_id)
    if area_id:
        consulta = consulta.filter(Area.id_area == area_id)
    if tipo:
        consulta = consulta.filter(Trabajador.tipo == tipo)
    return consulta.scalar() or 0


def _horas_de_filas(filas: list) -> float:
    por_dia: dict[tuple[int, object], list] = defaultdict(list)
    for id_trabajador, fecha_hora, tipo, _medio in filas:
        por_dia[(id_trabajador, fecha_hora.date())].append((fecha_hora, tipo))

    total = timedelta()
    for lista in por_dia.values():
        abierto = None
        for fecha_hora, tipo in sorted(lista, key=lambda item: item[0]):
            if tipo == "ingreso":
                abierto = fecha_hora
            elif tipo == "salida" and abierto is not None:
                total += fecha_hora - abierto
                abierto = None
    return round(total.total_seconds() / 3600, 2)


def _agregados_anuales(
    sede_id: int | None,
    area_id: int | None,
    tipo: str | None,
) -> dict[int, dict]:
    """Conteos operativos de todos los años en una sola pasada."""
    inicio = datetime(2024, 1, 1)
    fin = datetime(2028, 1, 1)
    marcas = (
        db.session.query(
            func.strftime("%Y", Marca.fecha_hora).label("anio"),
            func.count(Marca.id_marca),
            func.sum(case((Marca.medio == "nfc", 1), else_=0)),
            func.count(func.distinct(Marca.id_trabajador)),
        )
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    incidencias = (
        db.session.query(
            func.strftime("%Y", Marca.fecha_hora).label("anio"),
            func.count(Incidencia.id_incidencia),
        )
        .join(Marca, Incidencia.id_marca == Marca.id_marca)
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        marcas = marcas.filter(Area.id_sede == sede_id)
        incidencias = incidencias.filter(Area.id_sede == sede_id)
    if area_id:
        marcas = marcas.filter(Area.id_area == area_id)
        incidencias = incidencias.filter(Area.id_area == area_id)
    if tipo:
        marcas = marcas.filter(Trabajador.tipo == tipo)
        incidencias = incidencias.filter(Trabajador.tipo == tipo)

    por_anio = {}
    for anio, total, nfc, trabajadores in marcas.group_by("anio").all():
        por_anio[int(anio)] = {
            "marcas": int(total),
            "nfc_marcas": int(nfc or 0),
            "trabajadores": int(trabajadores or 0),
            "incidencias": 0,
        }
    for anio, total in incidencias.group_by("anio").all():
        por_anio.setdefault(int(anio), {"marcas": 0, "nfc_marcas": 0, "trabajadores": 0})
        por_anio[int(anio)]["incidencias"] = int(total)
    for datos in por_anio.values():
        datos["calidad"] = (
            round(datos["incidencias"] / datos["marcas"] * 100, 2) if datos["marcas"] else 0.0
        )
        datos["nfc"] = (
            round(datos["nfc_marcas"] / datos["marcas"] * 100, 1) if datos["marcas"] else 0.0
        )
    return por_anio


def _estado_mes(anio: int, mes: int, marcas: int) -> dict:
    periodo = Periodo.query.filter_by(anio=anio, mes=mes).first()
    if periodo is None:
        etiqueta = "Sin datos" if not marcas else "Sin periodo"
        return {
            "label": etiqueta,
            "badge": ESTADOS_BADGE["sin datos" if not marcas else "sin periodo"],
            "escenario": "as_is",
            "es_simulacion": False,
        }
    estado = estado_periodo(periodo.estado)
    return {
        "label": estado["label"],
        "badge": estado["badge"],
        "escenario": periodo.escenario,
        "es_simulacion": periodo.es_simulacion,
    }


def resumen_mes(
    anio: int,
    mes: int,
    sede_id: int | None = None,
    area_id: int | None = None,
    tipo: str | None = None,
) -> dict:
    inicio, fin = _rango_mes(anio, mes)
    filas = _consulta_marcas(inicio, fin, sede_id, area_id, tipo).all()
    marcas = len(filas)
    incidencias = _consulta_incidencias(inicio, fin, sede_id, area_id, tipo)
    nfc = sum(1 for fila in filas if fila.medio == "nfc")
    estado = _estado_mes(anio, mes, marcas)
    return {
        "anio": anio,
        "mes": mes,
        "etiqueta": f"{MESES_LARGOS[mes - 1]} {anio}",
        "marcas": marcas,
        "incidencias": incidencias,
        "calidad": round(incidencias / marcas * 100, 2) if marcas else 0.0,
        "nfc": round(nfc / marcas * 100, 1) if marcas else 0.0,
        "horas": _horas_de_filas(filas),
        "trabajadores": len({fila.id_trabajador for fila in filas}),
        "estado": estado["label"],
        "badge": estado["badge"],
        "escenario": estado["escenario"],
        "es_simulacion": estado["es_simulacion"],
    }


def resumen_anual(
    anio: int,
    sede_id: int | None = None,
    area_id: int | None = None,
    tipo: str | None = None,
    meses: tuple[int, ...] = MESES,
) -> dict:
    inicio = datetime(anio, 1, 1)
    fin = datetime(anio + 1, 1, 1)
    seleccion = set(meses)
    filas = _consulta_marcas(inicio, fin, sede_id, area_id, tipo).all()
    marcas_por_mes = [0] * 12
    nfc_por_mes = [0] * 12
    horas_por_mes = [0.0] * 12
    trabajadores_por_mes = [set() for _ in range(12)]
    por_dia: dict[tuple[int, object], list] = defaultdict(list)

    for id_trabajador, fecha_hora, tipo_marca, medio in filas:
        indice = fecha_hora.month - 1
        marcas_por_mes[indice] += 1
        if medio == "nfc":
            nfc_por_mes[indice] += 1
        trabajadores_por_mes[indice].add(id_trabajador)
        por_dia[(id_trabajador, fecha_hora.date())].append((fecha_hora, tipo_marca))

    for lista in por_dia.values():
        abierto = None
        for fecha_hora, tipo_marca in sorted(lista, key=lambda item: item[0]):
            if tipo_marca == "ingreso":
                abierto = fecha_hora
            elif tipo_marca == "salida" and abierto is not None:
                horas_por_mes[fecha_hora.month - 1] += (fecha_hora - abierto).total_seconds()
                abierto = None

    consulta_incidencias = (
        db.session.query(
            func.strftime("%m", Marca.fecha_hora),
            func.count(Incidencia.id_incidencia),
        )
        .join(Incidencia, Incidencia.id_marca == Marca.id_marca)
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        consulta_incidencias = consulta_incidencias.filter(Area.id_sede == sede_id)
    if area_id:
        consulta_incidencias = consulta_incidencias.filter(Area.id_area == area_id)
    if tipo:
        consulta_incidencias = consulta_incidencias.filter(Trabajador.tipo == tipo)
    incidencias = {
        int(mes): int(total)
        for mes, total in consulta_incidencias.group_by(func.strftime("%m", Marca.fecha_hora)).all()
    }

    meses = []
    for mes in MESES:
        indice = mes - 1
        marcas = marcas_por_mes[indice]
        incidencia_mes = incidencias.get(mes, 0)
        estado = _estado_mes(anio, mes, marcas)
        meses.append(
            {
                "anio": anio,
                "mes": mes,
                "etiqueta": f"{MESES_LARGOS[mes - 1]} {anio}",
                "marcas": marcas,
                "incidencias": incidencia_mes,
                "calidad": round(incidencia_mes / marcas * 100, 2) if marcas else 0.0,
                "nfc": round(nfc_por_mes[indice] / marcas * 100, 1) if marcas else 0.0,
                "horas": round(horas_por_mes[indice] / 3600, 2),
                "trabajadores": len(trabajadores_por_mes[indice]),
                "estado": estado["label"],
                "badge": estado["badge"],
                "escenario": estado["escenario"],
                "es_simulacion": estado["es_simulacion"],
            }
        )

    total_marcas = sum(marcas_por_mes[mes - 1] for mes in seleccion)
    total_incidencias = sum(total for mes, total in incidencias.items() if mes in seleccion)
    total_nfc = sum(nfc_por_mes[mes - 1] for mes in seleccion)
    total_horas = sum(horas_por_mes[mes - 1] for mes in seleccion)
    trabajadores = (
        set().union(*(trabajadores_por_mes[mes - 1] for mes in seleccion)) if filas else set()
    )
    return {
        "anio": anio,
        "meses": meses,
        "total_marcas": total_marcas,
        "total_incidencias": total_incidencias,
        "calidad": round(total_incidencias / total_marcas * 100, 2) if total_marcas else 0.0,
        "nfc": round(total_nfc / total_marcas * 100, 1) if total_marcas else 0.0,
        "horas": round(total_horas / 3600, 2),
        "trabajadores": len(trabajadores),
    }


def opciones_anuales() -> dict:
    return {
        "anios": list(ANIOS),
        "sedes": Sede.query.filter_by(activa=True).order_by(Sede.nombre).all(),
        "areas": Area.query.order_by(Area.nombre).all(),
        "tipos": TIPOS_PERSONAL,
    }


def construir_anual(
    anio: int,
    sede_id: int | None = None,
    area_id: int | None = None,
    tipo: str | None = None,
    vista: str = "anual",
) -> dict:
    anio = anio if anio in ANIOS else 2026
    vista = vista if vista in SEMESTRES else "anual"
    meses_vista = SEMESTRES[vista]["meses"] if vista != "anual" else MESES
    indicadores = datos_indicadores_anuales()
    anual = resumen_anual(anio, sede_id, area_id, tipo, meses=meses_vista)
    eneros = [resumen_mes(year, 1, sede_id, area_id, tipo) for year in ANIOS]
    agregados = _agregados_anuales(sede_id, area_id, tipo)
    comparativa = []
    for year in ANIOS:
        operativo = agregados.get(year, {"marcas": 0, "incidencias": 0, "calidad": 0.0, "nfc": 0.0})
        ind = indicadores.get(year, {})
        comparativa.append(
            {
                "anio": year,
                "etiqueta": "Enero 2027 simulado" if year == 2027 else str(year),
                "marcas": operativo.get("marcas", 0),
                "incidencias": operativo.get("incidencias", 0),
                "calidad": operativo.get("calidad", 0.0),
                "nfc": operativo.get("nfc", 0.0),
                "oportunidad": ind.get("oportunidad", 0),
                "eficiencia": ind.get("eficiencia", 0),
                "calidad_kpi": ind.get("calidad", 0),
                "extraviadas": ind.get("extraviadas", 0),
                "costo": ind.get("costo", 0),
                "escenario": "TO-BE simulado" if year == 2027 else "AS-IS",
            }
        )

    chart_data = {
        "eneros": {
            "labels": [str(item["anio"]) for item in eneros],
            "calidad": [item["calidad"] for item in eneros],
            "nfc": [item["nfc"] for item in eneros],
            "incidencias": [item["incidencias"] for item in eneros],
        },
        "anual": {
            "labels": [str(item["anio"]) for item in comparativa],
            "oportunidad": [item["oportunidad"] for item in comparativa],
            "calidad": [item["calidad_kpi"] for item in comparativa],
            "nfc": [item["nfc"] for item in comparativa],
        },
    }
    return {
        "anio": anio,
        "resumen": anual,
        "meses": [mes for mes in anual["meses"] if mes["mes"] in meses_vista],
        "vista": vista,
        "vista_codigo": SEMESTRES[vista]["codigo"] if vista != "anual" else "Anual",
        "vista_label": SEMESTRES[vista]["nombre"] if vista != "anual" else "Anual",
        "vista_rango": SEMESTRES[vista]["rango"] if vista != "anual" else "Enero – diciembre",
        "eneros": eneros,
        "comparativa": comparativa,
        "chart_data": chart_data,
        "indicadores": indicadores,
        "filtros": {
            "sede": sede_id,
            "area": area_id,
            "tipo": tipo,
        },
        "tiene_filtros": bool(sede_id or area_id or tipo),
    }


def _resumen_filas(datos: dict) -> list[list]:
    filas = [["Mes", "Marcas", "Incidencias", "Calidad %", "NFC %", "Horas", "Estado", "Escenario"]]
    for mes in datos["meses"]:
        filas.append(
            [
                mes["etiqueta"],
                mes["marcas"],
                mes["incidencias"],
                mes["calidad"],
                mes["nfc"],
                mes["horas"],
                mes["estado"],
                "TO-BE simulado" if mes["es_simulacion"] else "AS-IS",
            ]
        )
    resumen = datos["resumen"]
    etiqueta_total = (
        f"Total {datos['anio']}"
        if datos["vista"] == "anual"
        else f"Total {datos['vista_codigo']} {datos['anio']}"
    )
    filas.append(
        [
            etiqueta_total,
            resumen["total_marcas"],
            resumen["total_incidencias"],
            resumen["calidad"],
            resumen["nfc"],
            resumen["horas"],
            "—",
            "Meta TO-BE" if datos["anio"] == 2027 else "AS-IS",
        ]
    )
    return filas


def generar_csv_anual(datos: dict) -> bytes:
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=",", lineterminator="\n")
    titulo = (
        "Consolidado anual UTSM"
        if datos["vista"] == "anual"
        else f"Consolidado {datos['vista_codigo']} UTSM"
    )
    escritor.writerow([titulo, datos["anio"]])
    if datos["tiene_filtros"]:
        escritor.writerow(["Filtros aplicados a la operación", datos["filtros"]])
    escritor.writerow([])
    escritor.writerows(_resumen_filas(datos))
    if datos["vista"] != "anual":
        return salida.getvalue().encode("utf-8-sig")
    escritor.writerow([])
    escritor.writerow(["Comparación enero"])
    escritor.writerow(["Año", "Marcas", "Incidencias", "Calidad %", "NFC %", "Horas", "Escenario"])
    for item in datos["eneros"]:
        escritor.writerow(
            [
                item["anio"],
                item["marcas"],
                item["incidencias"],
                item["calidad"],
                item["nfc"],
                item["horas"],
                "TO-BE simulado" if item["es_simulacion"] else "AS-IS",
            ]
        )
    escritor.writerow([])
    escritor.writerow(["Comparación anual KPI"])
    escritor.writerow(
        [
            "Año",
            "Oportunidad %",
            "Eficiencia h",
            "Calidad KPI %",
            "Extraviadas %",
            "Costo S/",
            "NFC %",
            "Escenario",
        ]
    )
    for item in datos["comparativa"]:
        escritor.writerow(
            [
                item["anio"],
                item["oportunidad"],
                item["eficiencia"],
                item["calidad_kpi"],
                item["extraviadas"],
                item["costo"],
                item["nfc"],
                item["escenario"],
            ]
        )
    return salida.getvalue().encode("utf-8-sig")


def generar_excel_anual(datos: dict) -> io.BytesIO:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Mensual"
    borde = Border(
        left=Side(style="thin", color="D7E5DA"),
        right=Side(style="thin", color="D7E5DA"),
        top=Side(style="thin", color="D7E5DA"),
        bottom=Side(style="thin", color="D7E5DA"),
    )
    relleno = PatternFill("solid", fgColor="E9F2EA")
    fuente = Font(bold=True, color="14532D")
    filas = _resumen_filas(datos)
    hoja.append(filas[0])
    for celda in hoja[1]:
        celda.fill = relleno
        celda.font = fuente
        celda.border = borde
    for fila in filas[1:]:
        hoja.append(fila)
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    for indice, ancho in enumerate([18, 12, 12, 12, 10, 12, 14, 18], start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho

    if datos["vista"] == "anual":
        enero = libro.create_sheet("Enero")
        enero.append(["Año", "Marcas", "Incidencias", "Calidad %", "NFC %", "Horas", "Escenario"])
        for celda in enero[1]:
            celda.fill = relleno
            celda.font = fuente
            celda.border = borde
        for item in datos["eneros"]:
            enero.append(
                [
                    item["anio"],
                    item["marcas"],
                    item["incidencias"],
                    item["calidad"],
                    item["nfc"],
                    item["horas"],
                    "TO-BE simulado" if item["es_simulacion"] else "AS-IS",
                ]
            )
        enero.freeze_panes = "A2"
        for indice, ancho in enumerate([10, 12, 12, 12, 10, 12, 18], start=1):
            enero.column_dimensions[get_column_letter(indice)].width = ancho

        indicadores = libro.create_sheet("Indicadores")
        indicadores.append(
            [
                "Año",
                "Oportunidad %",
                "Eficiencia h",
                "Calidad KPI %",
                "Extraviadas %",
                "Costo S/",
                "NFC %",
                "Escenario",
            ]
        )
        for celda in indicadores[1]:
            celda.fill = relleno
            celda.font = fuente
            celda.border = borde
        for item in datos["comparativa"]:
            indicadores.append(
                [
                    item["anio"],
                    item["oportunidad"],
                    item["eficiencia"],
                    item["calidad_kpi"],
                    item["extraviadas"],
                    item["costo"],
                    item["nfc"],
                    item["escenario"],
                ]
            )
        indicadores.freeze_panes = "A2"
        for indice, ancho in enumerate([10, 14, 14, 14, 14, 12, 10, 18], start=1):
            indicadores.column_dimensions[get_column_letter(indice)].width = ancho

    salida = io.BytesIO()
    libro.save(salida)
    salida.seek(0)
    return salida


def generar_pdf_anual(datos: dict) -> bytes:
    from flask import render_template
    from weasyprint import HTML

    html = render_template(
        "reports/pdf_anual.html",
        datos=datos,
        generado=datetime.now(),
    )
    return HTML(string=html).write_pdf()
