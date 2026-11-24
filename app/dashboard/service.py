"""Indicadores KPI, series históricas y operación del periodo."""

from datetime import datetime

from sqlalchemy import func

from ..models import Area, Incidencia, IndicadorPeriodo, Marca, Trabajador

# Valores de línea base y meta del documento v6 (Tabla 9). 2027 es proyección.
KPI_HISTORICO = {
    2024: {
        "oportunidad": 20.0,
        "eficiencia": 130.0,
        "calidad": 15.0,
        "extraviadas": 18.0,
        "costo": 2200.0,
        "nfc": 0.0,
    },
    2025: {
        "oportunidad": 30.0,
        "eficiencia": 125.0,
        "calidad": 13.5,
        "extraviadas": 16.0,
        "costo": 2100.0,
        "nfc": 0.0,
    },
    2026: {
        "oportunidad": 40.0,
        "eficiencia": 118.0,
        "calidad": 12.0,
        "extraviadas": 15.0,
        "costo": 2020.40,
        "nfc": 0.0,
    },
    2027: {
        "oportunidad": 95.0,
        "eficiencia": 34.0,
        "calidad": 6.0,
        "extraviadas": 2.0,
        "costo": 738.61,
        "nfc": 95.0,
    },
}

METAS = {
    "oportunidad": 95.0,
    "eficiencia": 34.0,
    "calidad": 6.0,
}

KPI_DEFS = [
    {
        "clave": "oportunidad",
        "nombre": "Oportunidad del cierre",
        "unidad": "%",
        "meta_texto": "≥ 95 %",
        "mejor": "mayor",
        "descripcion": "Consolidaciones enviadas a planilla dentro de dos días hábiles.",
    },
    {
        "clave": "eficiencia",
        "nombre": "Eficiencia de consolidación",
        "unidad": "h",
        "meta_texto": "≤ 34 h/mes",
        "mejor": "menor",
        "descripcion": "Horas mensuales de consolidación y corrección.",
    },
    {
        "clave": "calidad",
        "nombre": "Calidad de las marcaciones",
        "unidad": "%",
        "meta_texto": "≤ 6 %",
        "mejor": "menor",
        "descripcion": "Porcentaje de marcaciones con incidencia.",
    },
]

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


def datos_indicadores_anuales() -> dict[int, dict]:
    """Lee los indicadores anuales de la base y usa la Tabla 9 como respaldo."""
    datos = {anio: dict(valores) for anio, valores in KPI_HISTORICO.items()}
    for fila in IndicadorPeriodo.query.filter_by(mes=0).order_by(IndicadorPeriodo.anio):
        datos[fila.anio] = {
            "oportunidad": fila.oportunidad,
            "eficiencia": fila.eficiencia_h,
            "calidad": fila.calidad_pct,
            "extraviadas": fila.extraviadas_pct,
            "costo": fila.costo,
            "nfc": fila.adopcion_nfc,
        }
    return datos


def _estado_kpi(clave: str, valor: float) -> tuple[str, str]:
    if clave == "oportunidad":
        if valor >= 95:
            return "jade", "En meta"
        if valor >= 80:
            return "brass", "Cerca de la meta"
        return "clay", "Bajo la meta"
    if clave == "eficiencia":
        if valor <= 34:
            return "jade", "En meta"
        if valor <= 50:
            return "brass", "Cerca de la meta"
        return "clay", "Sobre la meta"
    if valor <= 6:
        return "jade", "En meta"
    if valor <= 10:
        return "brass", "Cerca de la meta"
    return "clay", "Sobre la meta"


def _variacion(clave: str, anio: int, datos: dict[int, dict] | None = None) -> float | None:
    datos = datos or datos_indicadores_anuales()
    if anio - 1 not in datos or anio not in datos:
        return None
    return round(datos[anio][clave] - datos[anio - 1][clave], 2)


def kpi_anio(anio: int) -> list[dict]:
    datos = datos_indicadores_anuales()
    anio = anio if anio in datos else 2026
    tarjetas = []
    for definicion in KPI_DEFS:
        clave = definicion["clave"]
        valor = datos[anio][clave]
        badge, estado = _estado_kpi(clave, valor)
        tarjetas.append(
            {
                **definicion,
                "valor": valor,
                "valor_texto": f"{valor:g}",
                "meta": METAS[clave],
                "badge": badge,
                "estado": estado,
                "variacion": _variacion(clave, anio, datos),
                "proyeccion": anio == 2027,
            }
        )
    return tarjetas


def contexto_anio(anio: int) -> dict:
    datos = datos_indicadores_anuales()
    anio = anio if anio in datos else 2026
    return {
        "costo": datos[anio]["costo"],
        "extraviadas": datos[anio]["extraviadas"],
        "nfc": datos[anio]["nfc"],
        "anio": anio,
        "proyeccion": anio == 2027,
    }


def series_historicas(metrica: str) -> dict:
    if metrica not in METAS:
        metrica = "calidad"
    datos = datos_indicadores_anuales()
    anios = sorted(datos)
    definicion = next(item for item in KPI_DEFS if item["clave"] == metrica)
    return {
        "metrica": metrica,
        "nombre": definicion["nombre"],
        "unidad": definicion["unidad"],
        "meta": METAS[metrica],
        "labels": [str(anio) for anio in anios],
        "datos": [datos[anio][metrica] for anio in anios],
    }


def heatmap_historico() -> dict:
    datos = datos_indicadores_anuales()
    anios = sorted(datos)
    return {
        "x_labels": [str(anio) for anio in anios],
        "y_labels": [definicion["nombre"] for definicion in KPI_DEFS],
        "matrix": [[datos[anio][definicion["clave"]] for anio in anios] for definicion in KPI_DEFS],
        "units": [definicion["unidad"] for definicion in KPI_DEFS],
        "mejor": [definicion["mejor"] for definicion in KPI_DEFS],
        "meta": [METAS[definicion["clave"]] for definicion in KPI_DEFS],
    }


def rango_operacion(anio: int, mes: int | None) -> tuple[datetime, datetime, str]:
    if anio == 2027 and mes is None:
        return datetime(2027, 1, 1), datetime(2027, 2, 1), "Enero 2027 · TO-BE simulado"
    if mes:
        inicio = datetime(anio, mes, 1)
        if mes == 12:
            fin = datetime(anio + 1, 1, 1)
        else:
            fin = datetime(anio, mes + 1, 1)
        return inicio, fin, f"{MESES[mes - 1]} {anio}"
    return datetime(anio, 1, 1), datetime(anio + 1, 1, 1), f"Año {anio}"


def operacion_periodo(
    anio: int,
    mes: int | None = None,
    sede_id: int | None = None,
    area_id: int | None = None,
    tipo: str | None = None,
) -> dict:
    inicio, fin, etiqueta = rango_operacion(anio, mes)

    consulta_marcas = (
        Marca.query.join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        consulta_marcas = consulta_marcas.filter(Marca.id_sede == sede_id)
    if area_id:
        consulta_marcas = consulta_marcas.filter(Trabajador.id_area == area_id)
    if tipo:
        consulta_marcas = consulta_marcas.filter(Trabajador.tipo == tipo)
    marcas_por_area = dict(
        consulta_marcas.with_entities(Area.nombre, func.count(Marca.id_marca))
        .group_by(Area.nombre)
        .all()
    )

    consulta_incidencias = (
        Incidencia.query.join(Marca, Incidencia.id_marca == Marca.id_marca)
        .join(Trabajador, Marca.id_trabajador == Trabajador.id_trabajador)
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    )
    if sede_id:
        consulta_incidencias = consulta_incidencias.filter(Marca.id_sede == sede_id)
    if area_id:
        consulta_incidencias = consulta_incidencias.filter(Trabajador.id_area == area_id)
    if tipo:
        consulta_incidencias = consulta_incidencias.filter(Trabajador.tipo == tipo)
    incidencias_por_area = dict(
        consulta_incidencias.with_entities(Area.nombre, func.count(Incidencia.id_incidencia))
        .group_by(Area.nombre)
        .all()
    )

    consulta_areas = Area.query
    if sede_id:
        consulta_areas = consulta_areas.filter(Area.id_sede == sede_id)
    if area_id:
        consulta_areas = consulta_areas.filter(Area.id_area == area_id)
    areas = consulta_areas.order_by(Area.nombre).all()
    labels = [area.nombre for area in areas]
    marcas = [marcas_por_area.get(nombre, 0) for nombre in labels]
    incidencias = [incidencias_por_area.get(nombre, 0) for nombre in labels]
    total_marcas = sum(marcas)
    total_incidencias = sum(incidencias)
    total_nfc = (
        consulta_marcas.filter(Marca.medio == "nfc")
        .with_entities(func.count(Marca.id_marca))
        .scalar()
        or 0
    )
    calidad = round(total_incidencias / total_marcas * 100, 2) if total_marcas else 0.0
    adopcion_nfc = round(total_nfc / total_marcas * 100, 1) if total_marcas else 0.0
    return {
        "etiqueta": etiqueta,
        "labels": labels,
        "marcas": marcas,
        "incidencias": incidencias,
        "total_marcas": total_marcas,
        "total_incidencias": total_incidencias,
        "total_nfc": total_nfc,
        "calidad_operativa": calidad,
        "nfc_adopcion": adopcion_nfc,
    }


def opciones_filtros() -> dict:
    from ..models import Sede

    return {
        "anios": sorted(datos_indicadores_anuales()),
        "meses": [(numero, MESES[numero - 1]) for numero in range(1, 13)],
        "sedes": Sede.query.order_by(Sede.nombre).all(),
        "areas": Area.query.order_by(Area.nombre).all(),
        "tipos": [
            ("admin", "Administrativo"),
            ("docente_tc", "Docente TC"),
            ("docente_tp", "Docente TP"),
        ],
    }
