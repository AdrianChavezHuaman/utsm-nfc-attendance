"""Consolidado mensual, exportaciones y cierre de periodo."""

import calendar
import csv
import io
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app, render_template
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import func

from ..extensions import db
from ..kiosk.rules import periodo_bloqueado
from ..models import Consolidado, Incidencia, Marca, Periodo, Trabajador
from ..utils.audit import registrar_auditoria
from ..utils.helpers import (
    estado_incidencia,
    estado_justificacion_label,
    tipo_incidencia_label,
)

MESES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


def validar_periodo(anio: int, mes: int) -> None:
    if not 2000 <= anio <= 2100 or not 1 <= mes <= 12:
        raise ValueError("El periodo solicitado no es válido.")


def rango_mes(anio: int, mes: int) -> tuple[datetime, datetime]:
    validar_periodo(anio, mes)
    inicio = datetime(anio, mes, 1)
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    fin = datetime(anio, mes, ultimo_dia, 23, 59, 59, 999999) + timedelta(microseconds=1)
    return inicio, fin


def opciones_periodos() -> list[tuple[int, int]]:
    opciones: set[tuple[int, int]] = set()
    filas = (
        db.session.query(
            func.strftime("%Y", Marca.fecha_hora),
            func.strftime("%m", Marca.fecha_hora),
        )
        .distinct()
        .all()
    )
    for anio, mes in filas:
        if anio and mes:
            opciones.add((int(anio), int(mes)))
    for periodo in Periodo.query.all():
        opciones.add((periodo.anio, periodo.mes))
    if not opciones:
        hoy = date.today()
        opciones.add((hoy.year, hoy.month))
    return sorted(opciones, reverse=True)


def periodo_por_defecto() -> tuple[int, int]:
    """Prioriza el periodo abierto más reciente; si no hay, usa el mes anterior."""
    abierto = (
        Periodo.query.filter_by(estado="abierto")
        .order_by(Periodo.anio.desc(), Periodo.mes.desc())
        .first()
    )
    if abierto is not None:
        return abierto.anio, abierto.mes
    hoy = date.today()
    primer_dia = date(hoy.year, hoy.month, 1)
    anterior = primer_dia - timedelta(days=1)
    return anterior.year, anterior.month


def obtener_periodo(anio: int, mes: int, crear: bool = True) -> Periodo | None:
    validar_periodo(anio, mes)
    periodo = Periodo.query.filter_by(anio=anio, mes=mes).first()
    if periodo is None and crear:
        periodo = Periodo(anio=anio, mes=mes, estado="abierto")
        db.session.add(periodo)
        db.session.commit()
    return periodo


def calcular_horas_marcas(marcas) -> float:
    """Suma las parejas ingreso-salida del conjunto de marcas."""
    por_dia: dict[date, list] = defaultdict(list)
    for marca in marcas:
        por_dia[marca.fecha_hora.date()].append(marca)

    total = timedelta()
    for dia in sorted(por_dia):
        abierto = None
        for marca in sorted(por_dia[dia], key=lambda item: item.fecha_hora):
            if marca.tipo == "ingreso":
                abierto = marca
            elif marca.tipo == "salida" and abierto is not None:
                total += marca.fecha_hora - abierto.fecha_hora
                abierto = None
    return round(total.total_seconds() / 3600, 2)


def calcular_horas_trabajador(trabajador, anio: int, mes: int) -> float:
    inicio, fin = rango_mes(anio, mes)
    marcas = (
        Marca.query.filter(
            Marca.id_trabajador == trabajador.id_trabajador,
            Marca.fecha_hora >= inicio,
            Marca.fecha_hora < fin,
        )
        .order_by(Marca.fecha_hora.asc())
        .all()
    )
    return calcular_horas_marcas(marcas)


def detectar_faltantes(anio: int, mes: int) -> list[dict]:
    """Detecta parejas incompletas del mes sin modificar la base."""
    inicio, fin = rango_mes(anio, mes)
    marcas = (
        Marca.query.filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
        .order_by(Marca.id_trabajador, Marca.fecha_hora)
        .all()
    )
    por_trabajador: dict[int, list] = defaultdict(list)
    for marca in marcas:
        por_trabajador[marca.id_trabajador].append(marca)

    faltantes: list[dict] = []
    for id_trabajador, lista in por_trabajador.items():
        por_dia: dict[date, list] = defaultdict(list)
        for marca in lista:
            por_dia[marca.fecha_hora.date()].append(marca)
        for dia in sorted(por_dia):
            abierto = None
            for marca in sorted(por_dia[dia], key=lambda item: item.fecha_hora):
                if marca.tipo == "ingreso":
                    if abierto is not None:
                        faltantes.append(
                            {
                                "id_trabajador": id_trabajador,
                                "fecha": dia,
                                "tipo": "falta_salida",
                                "id_marca": abierto.id_marca,
                            }
                        )
                    abierto = marca
                elif abierto is None:
                    faltantes.append(
                        {
                            "id_trabajador": id_trabajador,
                            "fecha": dia,
                            "tipo": "falta_entrada",
                            "id_marca": marca.id_marca,
                        }
                    )
                else:
                    abierto = None
            if abierto is not None:
                faltantes.append(
                    {
                        "id_trabajador": id_trabajador,
                        "fecha": dia,
                        "tipo": "falta_salida",
                        "id_marca": abierto.id_marca,
                    }
                )
    return faltantes


def construir_resumen(anio: int, mes: int) -> dict:
    """Calcula horas, incidencias y excepciones de todos los trabajadores."""
    inicio, fin = rango_mes(anio, mes)
    marcas = (
        Marca.query.filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
        .order_by(Marca.fecha_hora.asc())
        .all()
    )
    incidencias = (
        Incidencia.query.join(Marca, Incidencia.id_marca == Marca.id_marca)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
        .order_by(Marca.fecha_hora.asc(), Incidencia.id_incidencia.asc())
        .all()
    )

    marcas_por_trabajador: dict[int, list] = defaultdict(list)
    for marca in marcas:
        marcas_por_trabajador[marca.id_trabajador].append(marca)
    incidencias_por_trabajador: dict[int, list] = defaultdict(list)
    for incidencia in incidencias:
        incidencias_por_trabajador[incidencia.id_trabajador].append(incidencia)

    filas = []
    total_horas = 0.0
    con_marcas = 0
    for trabajador in Trabajador.query.filter_by(activo=True).order_by(Trabajador.nombres):
        marcas_trabajador = marcas_por_trabajador.get(trabajador.id_trabajador, [])
        incidencias_trabajador = incidencias_por_trabajador.get(trabajador.id_trabajador, [])
        pendientes = [
            incidencia
            for incidencia in incidencias_trabajador
            if incidencia.estado in {"pendiente", "rechazada"}
        ]
        horas = calcular_horas_marcas(marcas_trabajador)
        if marcas_trabajador:
            con_marcas += 1
        total_horas += horas
        filas.append(
            {
                "trabajador": trabajador,
                "horas": horas,
                "marcas": len(marcas_trabajador),
                "incidencias": len(incidencias_trabajador),
                "pendientes": len(pendientes),
            }
        )

    excepciones = [
        incidencia for incidencia in incidencias if incidencia.estado in {"pendiente", "rechazada"}
    ]
    return {
        "anio": anio,
        "mes": mes,
        "etiqueta": f"{MESES[mes - 1]} {anio}",
        "filas": filas,
        "marcas": marcas,
        "incidencias": incidencias,
        "excepciones": excepciones,
        "total_horas": round(total_horas, 2),
        "trabajadores_con_marcas": con_marcas,
        "total_trabajadores": len(filas),
        "total_incidencias": len(incidencias),
        "total_excepciones": len(excepciones),
    }


def _formato_horas(valor: float) -> str:
    return f"{valor:.2f}"


def generar_csv_planilla(anio: int, mes: int, resumen: dict | None = None) -> bytes:
    resumen = resumen or construir_resumen(anio, mes)
    salida = io.StringIO()
    escritor = csv.writer(salida, delimiter=",", lineterminator="\n")
    escritor.writerow(
        [
            "Periodo",
            "DNI",
            "Trabajador",
            "Cargo",
            "Tipo",
            "Area",
            "Sede",
            "Horas trabajadas",
            "Incidencias",
            "Excepciones pendientes",
        ]
    )
    for fila in resumen["filas"]:
        trabajador = fila["trabajador"]
        escritor.writerow(
            [
                f"{mes:02d}/{anio}",
                trabajador.dni,
                trabajador.nombres,
                trabajador.cargo,
                trabajador.tipo,
                trabajador.area.nombre,
                trabajador.area.sede.nombre,
                _formato_horas(fila["horas"]),
                fila["incidencias"],
                fila["pendientes"],
            ]
        )
    return salida.getvalue().encode("utf-8-sig")


def generar_excel_detallado(anio: int, mes: int, resumen: dict | None = None) -> io.BytesIO:
    resumen = resumen or construir_resumen(anio, mes)
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Resumen"

    borde = Border(
        left=Side(style="thin", color="D7E5DA"),
        right=Side(style="thin", color="D7E5DA"),
        top=Side(style="thin", color="D7E5DA"),
        bottom=Side(style="thin", color="D7E5DA"),
    )
    relleno = PatternFill("solid", fgColor="E9F2EA")
    fuente_cabecera = Font(bold=True, color="14532D")
    cabeceras = [
        "DNI",
        "Trabajador",
        "Cargo",
        "Tipo",
        "Área",
        "Sede",
        "Horas trabajadas",
        "Marcas",
        "Incidencias",
        "Excepciones pendientes",
    ]
    hoja.append(cabeceras)
    for celda in hoja[1]:
        celda.fill = relleno
        celda.font = fuente_cabecera
        celda.border = borde
        celda.alignment = Alignment(vertical="center")
    for fila in resumen["filas"]:
        trabajador = fila["trabajador"]
        hoja.append(
            [
                trabajador.dni,
                trabajador.nombres,
                trabajador.cargo,
                trabajador.tipo,
                trabajador.area.nombre,
                trabajador.area.sede.nombre,
                fila["horas"],
                fila["marcas"],
                fila["incidencias"],
                fila["pendientes"],
            ]
        )
    hoja.freeze_panes = "A2"
    hoja.auto_filter.ref = hoja.dimensions
    for indice, ancho in enumerate([12, 32, 28, 14, 32, 22, 16, 10, 12, 20], start=1):
        hoja.column_dimensions[get_column_letter(indice)].width = ancho
    for fila in hoja.iter_rows(min_row=2, min_col=7, max_col=7):
        for celda in fila:
            celda.number_format = "0.00"

    hoja_incidencias = libro.create_sheet("Incidencias")
    cabeceras_incidencias = [
        "ID",
        "Fecha",
        "DNI",
        "Trabajador",
        "Área",
        "Tipo",
        "Estado",
        "Justificación",
        "Observación",
    ]
    hoja_incidencias.append(cabeceras_incidencias)
    for celda in hoja_incidencias[1]:
        celda.fill = relleno
        celda.font = fuente_cabecera
        celda.border = borde
    for incidencia in resumen["incidencias"]:
        justificacion = incidencia.justificacion
        hoja_incidencias.append(
            [
                incidencia.id_incidencia,
                incidencia.marca.fecha_hora.strftime("%d/%m/%Y %H:%M"),
                incidencia.trabajador.dni,
                incidencia.trabajador.nombres,
                incidencia.trabajador.area.nombre,
                tipo_incidencia_label(incidencia.tipo),
                estado_incidencia(incidencia)["label"],
                estado_justificacion_label(justificacion.estado)
                if justificacion
                else "Sin justificación",
                incidencia.observacion or "",
            ]
        )
    hoja_incidencias.freeze_panes = "A2"
    hoja_incidencias.auto_filter.ref = hoja_incidencias.dimensions
    for indice, ancho in enumerate([8, 18, 12, 30, 30, 20, 14, 18, 50], start=1):
        hoja_incidencias.column_dimensions[get_column_letter(indice)].width = ancho

    hoja_periodo = libro.create_sheet("Periodo")
    hoja_periodo.append(["Campo", "Valor"])
    for celda in hoja_periodo[1]:
        celda.fill = relleno
        celda.font = fuente_cabecera
        celda.border = borde
    periodo = obtener_periodo(anio, mes, crear=False)
    datos = [
        ("Periodo", resumen["etiqueta"]),
        ("Estado", periodo.estado.capitalize() if periodo else "Abierto"),
        ("Trabajadores", resumen["total_trabajadores"]),
        ("Trabajadores con marcas", resumen["trabajadores_con_marcas"]),
        ("Horas trabajadas", resumen["total_horas"]),
        ("Incidencias", resumen["total_incidencias"]),
        ("Excepciones pendientes", resumen["total_excepciones"]),
        ("Generado", datetime.now().strftime("%d/%m/%Y %H:%M")),
    ]
    for campo, valor in datos:
        hoja_periodo.append([campo, valor])
    hoja_periodo.column_dimensions["A"].width = 30
    hoja_periodo.column_dimensions["B"].width = 30

    salida = io.BytesIO()
    libro.save(salida)
    salida.seek(0)
    return salida


def generar_pdf_reporte(anio: int, mes: int, resumen: dict | None = None) -> bytes:
    resumen = resumen or construir_resumen(anio, mes)
    periodo = obtener_periodo(anio, mes, crear=False)
    html = render_template(
        "reports/pdf_reporte.html",
        resumen=resumen,
        periodo=periodo,
        generado=datetime.now(),
    )
    from weasyprint import HTML

    return HTML(string=html).write_pdf()


def _guardar_archivo(periodo: Periodo, tipo: str, contenido: bytes, extension: str, usuario):
    carpeta = Path(current_app.config["EXPORT_FOLDER"])
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = (
        f"consolidado_{periodo.anio}_{periodo.mes:02d}_{tipo}_"
        f"{datetime.now():%Y%m%d_%H%M%S}.{extension}"
    )
    ruta = carpeta / nombre
    ruta.write_bytes(contenido)
    registro = Consolidado(
        tipo=tipo,
        archivo=nombre,
        id_periodo=periodo.id_periodo,
        id_usuario=usuario.id_usuario if usuario is not None else None,
    )
    db.session.add(registro)
    return registro, ruta


def cerrar_periodo(anio: int, mes: int, usuario):
    """Archiva exportaciones y bloquea el periodo (R-07)."""
    periodo = obtener_periodo(anio, mes, crear=True)
    if periodo_bloqueado(periodo.estado):
        return False, f"El periodo {periodo.etiqueta} ya está {periodo.estado}.", periodo

    resumen = construir_resumen(anio, mes)
    rutas: list[Path] = []
    try:
        csv_bytes = generar_csv_planilla(anio, mes, resumen)
        excel_bytes = generar_excel_detallado(anio, mes, resumen).getvalue()
        pdf_bytes = generar_pdf_reporte(anio, mes, resumen)

        _registro, ruta_csv = _guardar_archivo(periodo, "csv", csv_bytes, "csv", usuario)
        rutas.append(ruta_csv)
        _registro, ruta_excel = _guardar_archivo(periodo, "excel", excel_bytes, "xlsx", usuario)
        rutas.append(ruta_excel)
        _registro, ruta_pdf = _guardar_archivo(periodo, "pdf", pdf_bytes, "pdf", usuario)
        rutas.append(ruta_pdf)

        periodo.estado = "cerrado"
        periodo.fecha_cierre = datetime.now()
        periodo.id_usuario_cierre = usuario.id_usuario
        periodo.total_trabajadores = resumen["total_trabajadores"]
        periodo.total_horas = resumen["total_horas"]
        periodo.total_incidencias = resumen["total_incidencias"]
        periodo.total_excepciones = resumen["total_excepciones"]
        db.session.commit()
    except Exception:  # pragma: no cover - defensa ante fallos de exportación
        db.session.rollback()
        for ruta in rutas:
            ruta.unlink(missing_ok=True)
        current_app.logger.exception("No se pudo cerrar el periodo.")
        return False, "No se pudo generar el consolidado. Intenta nuevamente.", periodo

    try:
        registrar_auditoria(
            "PERIODO_CERRADO",
            "periodo",
            periodo.id_periodo,
            datos_nuevos={
                "periodo": periodo.etiqueta,
                "total_horas": periodo.total_horas,
                "total_incidencias": periodo.total_incidencias,
            },
            id_usuario=usuario.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar el cierre del periodo.")

    return True, f"Periodo {periodo.etiqueta} cerrado y archivos generados.", periodo


def corregir_excepcion(incidencia: Incidencia, usuario, nota: str):
    """Cierra una excepción no resuelta durante el preconsolidado."""
    if incidencia.marca is None:
        return False, "La incidencia no tiene una marca asociada."
    anio = incidencia.marca.fecha_hora.year
    mes = incidencia.marca.fecha_hora.month
    periodo = obtener_periodo(anio, mes, crear=True)
    if periodo_bloqueado(periodo.estado):
        return False, f"El periodo {periodo.etiqueta} está {periodo.estado}; no admite cambios."
    if incidencia.estado not in {"pendiente", "rechazada"}:
        return False, "La incidencia no está pendiente de corrección."

    nota = (nota or "").strip()
    if len(nota) < 5:
        return False, "Escribe una nota de corrección de al menos 5 caracteres."

    anterior = incidencia.estado
    incidencia.estado = "cerrada"
    observacion = (incidencia.observacion or "").strip()
    incidencia.observacion = f"{observacion} Corrección del analista: {nota}".strip()
    try:
        db.session.commit()
    except Exception:  # pragma: no cover
        db.session.rollback()
        return False, "No se pudo guardar la corrección."

    try:
        registrar_auditoria(
            "EXCEPCION_CORREGIDA",
            "incidencia",
            incidencia.id_incidencia,
            datos_anteriores={"estado": anterior},
            datos_nuevos={"estado": "cerrada", "nota": nota},
            id_usuario=usuario.id_usuario,
        )
    except Exception:  # pragma: no cover
        current_app.logger.exception("No se pudo auditar la corrección.")

    return True, "Excepción corregida y cerrada."


def listar_periodos() -> list[Periodo]:
    return Periodo.query.order_by(Periodo.anio.desc(), Periodo.mes.desc()).all()
