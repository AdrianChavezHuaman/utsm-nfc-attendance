"""Genera la línea base AS-IS 2024-2026 y el escenario TO-BE de enero 2027.

2024-2026 simulan el control con huella dactilar: 19,520 marcas por mes,
0 % NFC y calidad 15 %, 13.5 % y 12 %. Enero 2027 es una simulación TO-BE:
95 % de adopción NFC, 6 % de incidencias y 1,171 marcaciones observadas.

Las tarjetas NFC se emiten el 27/12/2026. Diciembre 2026 queda abierto con 28
excepciones para demostrar el cierre; enero 2027 se cierra como escenario
simulado, no como medición real.

Uso:
    .venv/bin/python seeds/seed_historico.py
    .venv/bin/python seeds/seed_historico.py --anios 2024 2025 2026
    .venv/bin/python seeds/seed_historico.py --anios 2027
"""

import argparse
import calendar
import random
import sys
import time as time_module
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app
from sqlalchemy import delete, func, insert, inspect, select, text
from sqlalchemy.orm import joinedload

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.dashboard.service import KPI_HISTORICO  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Area,
    Horario,
    Incidencia,
    IndicadorPeriodo,
    Justificacion,
    Lector,
    Marca,
    Periodo,
    Sede,
    Trabajador,
    Usuario,
)
from app.utils.audit import registrar_auditoria  # noqa: E402
from seeds.seed_base import actualizar_horarios_variados, actualizar_tarjetas_nfc  # noqa: E402

ANIOS_VALIDOS = (2024, 2025, 2026, 2027)
ANIOS_AS_IS = (2024, 2025, 2026)
ANIO_TO_BE = 2027
OBJETIVO_MENSUAL = 19_520
TASAS_CALIDAD = {2024: 0.15, 2025: 0.135, 2026: 0.12, 2027: 0.06}
ADOPCION_NFC = {2024: 0.0, 2025: 0.0, 2026: 0.0, 2027: 0.95}
PROPORCION_FALTANTES = 0.01
PROPORCION_DUPLICADOS = 0.05
TAMANO_LOTE = 1000
JEFE_CORREO = "jefe@utsm.edu.pe"

# Diciembre 2026 se deja abierto para demostrar el preconsolidado y el cierre.
# Las incidencias restantes quedan cerradas; solo una muestra sigue pendiente.
PERIODOS_DEMO_ABIERTOS = {(2026, 12): 28}


def _rango_mes(anio: int, mes: int) -> tuple[datetime, datetime]:
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    inicio = datetime(anio, mes, 1)
    fin = datetime(anio, mes, ultimo_dia, 23, 59, 59, 999999) + timedelta(microseconds=1)
    return inicio, fin


def _meses_del_anio(anio: int, meses: list[int] | None = None) -> list[int]:
    if anio not in ANIOS_VALIDOS:
        raise ValueError(
            f"{anio} no está en la línea base: usa 2024-2026 para AS-IS o 2027 "
            "para el escenario TO-BE de enero."
        )
    if anio == ANIO_TO_BE:
        return [1]
    if meses:
        return [mes for mes in meses if 1 <= mes <= 12]
    return list(range(1, 13))


def _dias_habiles(anio: int, mes: int, limite_dias: int | None = None) -> list[date]:
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    dias = [
        date(anio, mes, dia)
        for dia in range(1, ultimo_dia + 1)
        if date(anio, mes, dia).weekday() < 5
    ]
    return dias[:limite_dias] if limite_dias else dias


def _lectores_por_sede() -> dict[tuple[int, str], Lector]:
    lectores: dict[tuple[int, str], Lector] = {}
    for lector in Lector.query.filter_by(estado="activo").order_by(Lector.id_lector):
        lectores.setdefault((lector.id_sede, lector.tipo), lector)
    return lectores


def _crear_marca(
    jornada: dict,
    tipo: str,
    fecha_hora: datetime,
    id_marca: int,
    rng: random.Random,
    tasa_nfc: float,
    lectores: dict[tuple[int, str], Lector],
) -> dict:
    tipo_lector = "entrada" if tipo == "ingreso" else "salida"
    lector = lectores.get((jornada["sede_id"], tipo_lector))
    if lector is None:
        raise ValueError(
            f"La sede {jornada['sede_id']} no tiene un lector de {tipo_lector}; "
            "ejecuta el seed base completo."
        )
    marca = {
        "id_marca": id_marca,
        "fecha_hora": fecha_hora,
        "tipo": tipo,
        "estado": "valida",
        "medio": "nfc" if tasa_nfc >= 1 or rng.random() < tasa_nfc else "huella",
        "id_trabajador": jornada["trabajador_id"],
        "id_lector": lector.id_lector,
        "id_sede": jornada["sede_id"],
    }
    jornada["marcas"].append(marca)
    return marca


def _adjuntar_incidencia(marca: dict, tipo: str, observacion: str, fecha: datetime) -> None:
    marca["estado"] = "observada"
    marca["_incidencia"] = {
        "tipo": tipo,
        "observacion": observacion,
        "fecha_creacion": fecha,
    }


def _calcular_horas(marcas: list[dict]) -> float:
    por_dia: dict[tuple[int, date], list[dict]] = defaultdict(list)
    for marca in marcas:
        por_dia[(marca["id_trabajador"], marca["fecha_hora"].date())].append(marca)

    total = timedelta()
    for lista in por_dia.values():
        abierto: datetime | None = None
        for marca in sorted(lista, key=lambda item: item["fecha_hora"]):
            if marca["tipo"] == "ingreso":
                abierto = marca["fecha_hora"]
            elif marca["tipo"] == "salida" and abierto is not None:
                total += marca["fecha_hora"] - abierto
                abierto = None
    return round(total.total_seconds() / 3600, 2)


def _insertar_lotes(modelo, filas: list[dict]) -> None:
    for inicio in range(0, len(filas), TAMANO_LOTE):
        db.session.execute(insert(modelo), filas[inicio : inicio + TAMANO_LOTE])


def _asegurar_esquema() -> None:
    """Agrega el escenario del periodo y la tabla de indicadores si faltan."""
    db.create_all()
    columnas = {columna["name"] for columna in inspect(db.engine).get_columns("periodo")}
    if "escenario" not in columnas:
        db.session.execute(
            text("ALTER TABLE periodo ADD COLUMN escenario VARCHAR(24) NOT NULL DEFAULT 'as_is'")
        )
        db.session.execute(
            text("CREATE INDEX IF NOT EXISTS ix_periodo_escenario ON periodo (escenario)")
        )
        db.session.commit()


def _sembrar_indicadores() -> None:
    """Sincroniza los indicadores anuales y el escenario simulado de enero 2027."""
    filas = [
        (anio, 0, "as_is", f"Línea base AS-IS {anio} con huella dactilar") for anio in ANIOS_AS_IS
    ]
    filas.extend(
        [
            (2027, 0, "meta", "Meta TO-BE 2027; no es una medición"),
            (2027, 1, "to_be_simulado", "Escenario simulado enero 2027 con NFC"),
        ]
    )

    for anio, mes, escenario, nota in filas:
        datos = KPI_HISTORICO[anio]
        indicador = IndicadorPeriodo.query.filter_by(
            anio=anio, mes=mes, escenario=escenario
        ).first()
        if indicador is None:
            indicador = IndicadorPeriodo(anio=anio, mes=mes, escenario=escenario)
            db.session.add(indicador)
        indicador.oportunidad = datos["oportunidad"]
        indicador.eficiencia_h = datos["eficiencia"]
        indicador.calidad_pct = datos["calidad"]
        indicador.extraviadas_pct = datos["extraviadas"]
        indicador.costo = datos["costo"]
        indicador.adopcion_nfc = datos["nfc"]
        indicador.fuente = "Tabla 9 y Tabla 17 del v6"
        indicador.nota = nota
    db.session.commit()


def _borrar_mes(anio: int, mes: int) -> None:
    inicio, fin = _rango_mes(anio, mes)
    periodo = Periodo.query.filter_by(anio=anio, mes=mes).first()
    if periodo is not None and periodo.consolidados:
        raise ValueError(
            f"El periodo {periodo.etiqueta} tiene archivos de cierre. "
            "No se reemplaza automáticamente."
        )

    ids_marcas = select(Marca.id_marca).where(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
    ids_incidencias = select(Incidencia.id_incidencia).where(Incidencia.id_marca.in_(ids_marcas))
    db.session.execute(
        delete(Justificacion).where(Justificacion.id_incidencia.in_(ids_incidencias))
    )
    db.session.execute(delete(Incidencia).where(Incidencia.id_marca.in_(ids_marcas)))
    db.session.execute(delete(Marca).where(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin))
    if periodo is not None:
        db.session.delete(periodo)
    db.session.commit()


def _generar_mes(
    anio: int,
    mes: int,
    trabajadores: list[Trabajador],
    horarios: dict[tuple[int, int], Horario],
    lectores: dict[tuple[int, str], Lector],
    objetivo: int,
    limite_dias: int | None,
    id_jefe: int | None,
    reemplazar: bool,
) -> dict | None:
    inicio, fin = _rango_mes(anio, mes)
    existentes = (
        db.session.query(func.count(Marca.id_marca))
        .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
        .scalar()
    )
    if existentes:
        if not reemplazar:
            return None
        _borrar_mes(anio, mes)

    dias = _dias_habiles(anio, mes, limite_dias)
    if not dias:
        return None

    jornadas: list[dict] = []
    for trabajador in trabajadores:
        for dia in dias:
            horario = horarios.get((trabajador.id_trabajador, dia.weekday()))
            if horario is None:
                continue
            entrada = datetime.combine(dia, horario.hora_entrada)
            salida = datetime.combine(dia, horario.hora_salida)
            if salida <= entrada:
                salida += timedelta(days=1)
            duracion = salida - entrada
            jornadas.append(
                {
                    "trabajador_id": trabajador.id_trabajador,
                    "sede_id": trabajador.area.id_sede,
                    "dia": dia,
                    "entrada": entrada,
                    "salida": salida,
                    "completa": duracion >= timedelta(hours=6),
                    "marcas": [],
                }
            )

    total_jornadas = len(jornadas)
    base = total_jornadas * 2
    if objetivo < base:
        raise ValueError(
            f"El objetivo de {objetivo} marcas es menor que las {base} marcas base "
            "del mes con los trabajadores y días seleccionados."
        )
    capacidad = base + total_jornadas * 2
    if objetivo > capacidad:
        raise ValueError(
            f"El objetivo de {objetivo} marcas supera la capacidad de {capacidad} "
            "marcas con una pausa por jornada."
        )

    rng = random.Random(20260000 + anio * 100 + mes)
    tasa = TASAS_CALIDAD[anio]
    tasa_nfc = ADOPCION_NFC[anio]
    incidentes_objetivo = round(objetivo * tasa)

    # Cada jornada puede recibir una pausa de dos marcas (salida + ingreso).
    pausas_base = (objetivo - base) // 2
    max_faltantes = max(0, (total_jornadas - pausas_base) * 2 // 3)
    faltantes = min(
        incidentes_objetivo,
        max(2, round(objetivo * PROPORCION_FALTANTES) // 2 * 2) if incidentes_objetivo >= 2 else 0,
        max_faltantes,
    )
    faltantes = faltantes // 2 * 2
    pausas = (objetivo - base + faltantes) // 2
    if pausas > total_jornadas:
        raise ValueError("No hay suficientes jornadas para alcanzar el objetivo solicitado.")

    completas = [jornada for jornada in jornadas if jornada["completa"]]
    parciales = [jornada for jornada in jornadas if not jornada["completa"]]
    rng.shuffle(completas)
    rng.shuffle(parciales)
    for jornada in (completas + parciales)[:pausas]:
        jornada["pausa"] = True

    sin_pausa = [jornada for jornada in jornadas if not jornada.get("pausa")]
    rng.shuffle(sin_pausa)
    for indice, jornada in enumerate(sin_pausa[:faltantes]):
        jornada["falta"] = "falta_salida" if indice % 2 == 0 else "falta_entrada"

    siguiente_id = (db.session.query(func.max(Marca.id_marca)).scalar() or 0) + 1
    for jornada in jornadas:
        fecha_entrada = jornada["entrada"] + timedelta(minutes=rng.randint(-3, 5))
        fecha_salida = jornada["salida"] + timedelta(minutes=rng.randint(-5, 10))
        _crear_marca(jornada, "ingreso", fecha_entrada, siguiente_id, rng, tasa_nfc, lectores)
        siguiente_id += 1
        if jornada.get("pausa"):
            punto_medio = fecha_entrada + (fecha_salida - fecha_entrada) / 2
            salida_pausa = punto_medio + timedelta(minutes=rng.randint(-10, 10))
            entrada_pausa = salida_pausa + timedelta(minutes=rng.randint(45, 75))
            if entrada_pausa >= fecha_salida - timedelta(minutes=5):
                entrada_pausa = fecha_salida - timedelta(minutes=5)
            _crear_marca(jornada, "salida", salida_pausa, siguiente_id, rng, tasa_nfc, lectores)
            siguiente_id += 1
            _crear_marca(jornada, "ingreso", entrada_pausa, siguiente_id, rng, tasa_nfc, lectores)
            siguiente_id += 1
        _crear_marca(jornada, "salida", fecha_salida, siguiente_id, rng, tasa_nfc, lectores)
        siguiente_id += 1
        jornada["marcas"].sort(key=lambda item: item["fecha_hora"])

    # Faltantes de entrada o salida: se retira una marca y se observa la pareja.
    for jornada in jornadas:
        falta = jornada.get("falta")
        if not falta:
            continue
        marcas = jornada["marcas"]
        if len(marcas) < 2:
            continue
        if falta == "falta_salida":
            marcas.pop()
            marca_observada = marcas[0]
            observacion = "Ingreso sin salida registrada; se detectó al cerrar la jornada."
        else:
            marcas.pop(0)
            marca_observada = marcas[-1]
            observacion = "Salida sin ingreso previo registrado en la jornada."
        _adjuntar_incidencia(
            marca_observada,
            falta,
            observacion,
            marca_observada["fecha_hora"] + timedelta(hours=2),
        )

    marcas = [marca for jornada in jornadas for marca in jornada["marcas"]]
    if len(marcas) != objetivo:
        raise AssertionError(f"Se planificaron {len(marcas)} marcas y se esperaban {objetivo}.")

    pendientes = incidentes_objetivo - faltantes
    duplicados = round(pendientes * PROPORCION_DUPLICADOS)
    fuera_horario = pendientes - duplicados

    candidatos_fuera: list[dict] = []
    for jornada in jornadas:
        validas = [marca for marca in jornada["marcas"] if marca["estado"] == "valida"]
        ingresos = [marca for marca in validas if marca["tipo"] == "ingreso"]
        salidas = [marca for marca in validas if marca["tipo"] == "salida"]
        if ingresos:
            candidatos_fuera.append(ingresos[0])
        if salidas and (not ingresos or salidas[-1] is not ingresos[0]):
            candidatos_fuera.append(salidas[-1])

    if len(candidatos_fuera) < fuera_horario:
        candidatos_fuera = [marca for marca in marcas if marca["estado"] == "valida"]
    if len(candidatos_fuera) < fuera_horario:
        raise ValueError("No hay marcas suficientes para distribuir las incidencias.")

    for marca in rng.sample(candidatos_fuera, fuera_horario):
        if marca["tipo"] == "ingreso":
            marca["fecha_hora"] += timedelta(minutes=rng.randint(11, 35))
            observacion = "Entrada fuera de la tolerancia de 10 minutos."
        else:
            marca["fecha_hora"] -= timedelta(minutes=rng.randint(10, 30))
            observacion = "Salida anticipada respecto del horario programado."
        _adjuntar_incidencia(
            marca,
            "fuera_horario",
            observacion,
            marca["fecha_hora"] + timedelta(hours=1),
        )

    candidatos_duplicado = [marca for marca in marcas if marca["estado"] == "valida"]
    for marca in rng.sample(candidatos_duplicado, min(duplicados, len(candidatos_duplicado))):
        _adjuntar_incidencia(
            marca,
            "duplicado",
            "Intento de marcación duplicada ignorado por el lector.",
            marca["fecha_hora"] + timedelta(minutes=2),
        )

    incidentes = [
        {
            "tipo": marca["_incidencia"]["tipo"],
            "estado": "cerrada",
            "observacion": marca["_incidencia"]["observacion"],
            "fecha_creacion": marca["_incidencia"]["fecha_creacion"],
            "id_marca": marca["id_marca"],
            "id_trabajador": marca["id_trabajador"],
        }
        for marca in marcas
        if "_incidencia" in marca
    ]
    if len(incidentes) != incidentes_objetivo:
        raise AssertionError(
            f"Se planificaron {len(incidentes)} incidencias y se esperaban {incidentes_objetivo}."
        )

    pendientes_demo = min(PERIODOS_DEMO_ABIERTOS.get((anio, mes), 0), len(incidentes))
    for incidencia in rng.sample(incidentes, pendientes_demo):
        incidencia["estado"] = "pendiente"

    horas = _calcular_horas(marcas)
    marcas_insertar = [
        {clave: valor for clave, valor in marca.items() if not clave.startswith("_")}
        for marca in marcas
    ]
    _insertar_lotes(Marca, marcas_insertar)
    _insertar_lotes(Incidencia, incidentes)

    periodo = Periodo.query.filter_by(anio=anio, mes=mes).first()
    if periodo is None:
        periodo = Periodo(anio=anio, mes=mes, creado_en=inicio)
        db.session.add(periodo)
    ultimo_dia = calendar.monthrange(anio, mes)[1]
    abierto = (anio, mes) in PERIODOS_DEMO_ABIERTOS
    periodo.estado = "abierto" if abierto else "cerrado"
    periodo.escenario = "to_be_simulado" if anio == ANIO_TO_BE else "as_is"
    periodo.fecha_cierre = None if abierto else datetime(anio, mes, ultimo_dia, 18, 0)
    periodo.id_usuario_cierre = None if abierto else id_jefe
    periodo.total_trabajadores = len({marca["id_trabajador"] for marca in marcas})
    periodo.total_horas = horas
    periodo.total_incidencias = len(incidentes)
    periodo.total_excepciones = pendientes_demo if abierto else 0

    db.session.commit()
    return {
        "anio": anio,
        "mes": mes,
        "marcas": len(marcas),
        "incidencias": len(incidentes),
        "excepciones": periodo.total_excepciones,
        "tasa": round(len(incidentes) / len(marcas) * 100, 3),
        "horas": horas,
        "nfc": round(sum(1 for m in marcas if m["medio"] == "nfc") / len(marcas) * 100, 1),
        "trabajadores": periodo.total_trabajadores,
        "estado": periodo.estado,
        "escenario": periodo.escenario,
    }


def _limpiar_periodos_vacios() -> list[str]:
    eliminados = []
    for periodo in Periodo.query.order_by(Periodo.anio, Periodo.mes).all():
        inicio, fin = _rango_mes(periodo.anio, periodo.mes)
        tiene_marcas = (
            db.session.query(func.count(Marca.id_marca))
            .filter(Marca.fecha_hora >= inicio, Marca.fecha_hora < fin)
            .scalar()
        )
        if not tiene_marcas and not periodo.consolidados:
            eliminados.append(periodo.etiqueta)
            db.session.delete(periodo)
    if eliminados:
        db.session.commit()
    return eliminados


def _preparar_demo_diciembre() -> None:
    """Conserva una incidencia del trabajador demo y una justificación pendiente."""
    periodo = Periodo.query.filter_by(anio=2026, mes=12, estado="abierto").first()
    if periodo is None:
        return
    area = Area.query.filter_by(nombre="Escuela de Administración").first()
    usuario_trabajador = Usuario.query.filter_by(correo="trabajador@utsm.edu.pe").first()
    usuario_coordinador = Usuario.query.filter_by(correo="coordinador@utsm.edu.pe").first()
    if area is None or usuario_trabajador is None or usuario_trabajador.trabajador is None:
        return

    trabajador_demo = usuario_trabajador.trabajador
    coordinador = usuario_coordinador.trabajador if usuario_coordinador else None
    excluidos = {trabajador_demo.id_trabajador}
    if coordinador is not None:
        excluidos.add(coordinador.id_trabajador)
    otro = next(
        (
            trabajador
            for trabajador in area.trabajadores
            if trabajador.id_trabajador not in excluidos
        ),
        None,
    )
    if otro is None:
        return

    inicio, fin = _rango_mes(2026, 12)
    pendientes = (
        Incidencia.query.join(Marca, Incidencia.id_marca == Marca.id_marca)
        .filter(
            Marca.fecha_hora >= inicio,
            Marca.fecha_hora < fin,
            Incidencia.estado == "pendiente",
        )
        .all()
    )
    if not pendientes:
        return
    ids_area = {trabajador.id_trabajador for trabajador in area.trabajadores}
    usados: set[int] = set()

    def incidencia_de(id_trabajador: int):
        return (
            Incidencia.query.join(Marca, Incidencia.id_marca == Marca.id_marca)
            .filter(
                Incidencia.id_trabajador == id_trabajador,
                Marca.fecha_hora >= inicio,
                Marca.fecha_hora < fin,
            )
            .order_by(Marca.fecha_hora)
            .first()
        )

    def forzar_pendiente(incidencia) -> bool:
        if incidencia is None:
            return False
        if incidencia.estado == "pendiente":
            return True
        reemplazo = next(
            (
                pendiente
                for pendiente in pendientes
                if pendiente.id_trabajador not in ids_area and pendiente.id_incidencia not in usados
            ),
            None,
        )
        if reemplazo is None:
            return False
        reemplazo.estado = "cerrada"
        incidencia.estado = "pendiente"
        usados.add(reemplazo.id_incidencia)
        return True

    incidencia_demo = incidencia_de(trabajador_demo.id_trabajador)
    forzar_pendiente(incidencia_demo)
    incidencia_otro = incidencia_de(otro.id_trabajador)
    if not forzar_pendiente(incidencia_otro):
        db.session.commit()
        return

    if Justificacion.query.filter_by(id_incidencia=incidencia_otro.id_incidencia).first():
        db.session.commit()
        return

    carpeta = Path(current_app.config["UPLOAD_FOLDER"])
    carpeta.mkdir(parents=True, exist_ok=True)
    archivo = f"demo_fase7_{uuid.uuid4().hex[:8]}.pdf"
    (carpeta / archivo).write_bytes(b"%PDF-1.4\n% Sustento de demostracion ShauLA EFC\n")
    db.session.add(
        Justificacion(
            motivo=(
                "El lector registró la salida fuera de la tolerancia. "
                "Adjunto el reporte de soporte del equipo."
            ),
            archivo=archivo,
            archivo_original="sustento_demo.pdf",
            estado="enviada",
            fecha_envio=datetime(2026, 12, 28, 9, 0),
            id_incidencia=incidencia_otro.id_incidencia,
        )
    )
    db.session.commit()


def generar_historico(
    anios: list[int] | None = None,
    objetivo_mensual: int = OBJETIVO_MENSUAL,
    reemplazar: bool = False,
    conservar_vacios: bool = False,
    limite_trabajadores: int | None = None,
    limite_dias: int | None = None,
    meses: list[int] | None = None,
) -> dict:
    """Genera los meses históricos faltantes y devuelve un resumen verificable."""
    if anios is None:
        anios = list(ANIOS_VALIDOS)
    for anio in anios:
        if anio not in ANIOS_VALIDOS:
            raise ValueError(
                f"{anio} no está en la línea base: usa 2024-2026 para AS-IS o 2027 "
                "para el escenario TO-BE de enero."
            )
    if objetivo_mensual < 4 or objetivo_mensual % 2:
        raise ValueError("El objetivo mensual debe ser un número par mayor o igual a 4.")

    _asegurar_esquema()
    actualizar_horarios_variados()
    actualizar_tarjetas_nfc()
    trabajadores = (
        Trabajador.query.options(joinedload(Trabajador.area))
        .filter_by(activo=True)
        .order_by(Trabajador.id_trabajador)
        .limit(limite_trabajadores)
        .all()
    )
    if not trabajadores:
        raise ValueError("No hay trabajadores activos; ejecuta primero el seed base.")

    horarios = {
        (horario.id_trabajador, horario.dia_semana): horario for horario in Horario.query.all()
    }
    lectores = _lectores_por_sede()
    jefe = Usuario.query.filter_by(correo=JEFE_CORREO).first()
    id_jefe = jefe.id_usuario if jefe else None

    generados: list[dict] = []
    omitidos: list[str] = []
    inicio_ejecucion = time_module.perf_counter()
    for anio in anios:
        for mes in _meses_del_anio(anio, meses):
            resultado = _generar_mes(
                anio,
                mes,
                trabajadores,
                horarios,
                lectores,
                objetivo_mensual,
                limite_dias,
                id_jefe,
                reemplazar,
            )
            if resultado is None:
                omitidos.append(f"{anio}-{mes:02d}")
            else:
                generados.append(resultado)
                print(
                    f"  {anio}-{mes:02d}  {resultado['marcas']:>6} marcas  "
                    f"{resultado['incidencias']:>5} incidencias  "
                    f"{resultado['tasa']:>5.2f} %  NFC {resultado['nfc']:>4.1f} %"
                )

    _sembrar_indicadores()
    _preparar_demo_diciembre()
    eliminados = [] if conservar_vacios else _limpiar_periodos_vacios()
    total_marcas = sum(item["marcas"] for item in generados)
    total_incidencias = sum(item["incidencias"] for item in generados)
    resumen = {
        "generados": generados,
        "omitidos": omitidos,
        "periodos_vacios_eliminados": eliminados,
        "totales": {
            "marcas": total_marcas,
            "incidencias": total_incidencias,
            "horas": round(sum(item["horas"] for item in generados), 2),
            "segundos": round(time_module.perf_counter() - inicio_ejecucion, 1),
        },
    }

    admin = Usuario.query.filter_by(correo="admin@utsm.edu.pe").first()
    if total_marcas and admin is not None:
        registrar_auditoria(
            "SEED_HISTORICO",
            "marca",
            None,
            datos_nuevos={
                "periodos": [f"{item['anio']}-{item['mes']:02d}" for item in generados],
                "marcas": total_marcas,
                "incidencias": total_incidencias,
            },
            id_usuario=admin.id_usuario,
        )
    return resumen


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Genera el AS-IS 2024-2026 y el TO-BE simulado de enero 2027."
    )
    parser.add_argument(
        "--anios",
        nargs="+",
        type=int,
        default=list(ANIOS_VALIDOS),
        help="Años a generar: 2024-2026 AS-IS y 2027 solo enero TO-BE.",
    )
    parser.add_argument(
        "--objetivo",
        type=int,
        default=OBJETIVO_MENSUAL,
        help="Marcas objetivo por mes completo (por defecto 19520).",
    )
    parser.add_argument(
        "--reemplazar",
        action="store_true",
        help="Borra y regenera los meses seleccionados que ya tengan marcas.",
    )
    parser.add_argument(
        "--conservar-vacios",
        action="store_true",
        help="No elimina periodos sin marcas ni archivos.",
    )
    parser.add_argument(
        "--limite-trabajadores",
        type=int,
        help="Límite de trabajadores para pruebas rápidas.",
    )
    parser.add_argument(
        "--limite-dias",
        type=int,
        help="Límite de días hábiles para pruebas rápidas.",
    )
    args = parser.parse_args()

    if any(anio not in ANIOS_VALIDOS for anio in args.anios):
        print("Error: usa 2024-2026 para AS-IS o 2027 para el escenario TO-BE de enero.")
        return 1

    aplicacion = create_app()
    with aplicacion.app_context():
        db.create_all()
        if not db.session.query(Sede.id_sede).first():
            print("No hay datos base. Ejecuta: make bootstrap")
            return 1
        print("Generando línea base histórica...")
        try:
            resumen = generar_historico(
                anios=args.anios,
                objetivo_mensual=args.objetivo,
                reemplazar=args.reemplazar,
                conservar_vacios=args.conservar_vacios,
                limite_trabajadores=args.limite_trabajadores,
                limite_dias=args.limite_dias,
            )
        except ValueError as error:
            print(f"Error: {error}")
            return 1

    totales = resumen["totales"]
    print(
        f"\nListo: {len(resumen['generados'])} periodos, "
        f"{totales['marcas']:,} marcas, {totales['incidencias']:,} incidencias, "
        f"{totales['horas']:,.2f} horas, {totales['segundos']} s."
    )
    if resumen["omitidos"]:
        print(f"Omitidos por tener datos: {', '.join(resumen['omitidos'])}")
    if resumen["periodos_vacios_eliminados"]:
        print(f"Periodos vacíos eliminados: {', '.join(resumen['periodos_vacios_eliminados'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
