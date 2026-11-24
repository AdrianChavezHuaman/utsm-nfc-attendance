"""Genera un mes de marcaciones simuladas para el preconsolidado.

Uso:
    .venv/bin/python scripts/demo_fase4.py
    .venv/bin/python scripts/demo_fase4.py --anio 2026 --mes 10

Por defecto usa el mes anterior. Si ya existen marcas en el periodo, no
duplica datos. Crea marcas normales, tardanzas y parejas incompletas para
que el analista pueda revisar excepciones y el jefe pueda cerrar el mes.
"""

import argparse
import calendar
import random
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Horario, Incidencia, Lector, Marca, Periodo, Trabajador  # noqa: E402


def _mes_anterior() -> tuple[int, int]:
    primer_dia = date.today().replace(day=1)
    anterior = primer_dia - timedelta(days=1)
    return anterior.year, anterior.month


def _lectores_por_sede_tipo() -> dict[tuple[int, str], Lector]:
    resultado = {}
    for lector in Lector.query.filter_by(estado="activo").order_by(Lector.id_lector):
        resultado.setdefault((lector.id_sede, lector.tipo), lector)
    return resultado


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera marcas simuladas de un mes.")
    anio_default, mes_default = _mes_anterior()
    parser.add_argument("--anio", type=int, default=anio_default)
    parser.add_argument("--mes", type=int, default=mes_default)
    args = parser.parse_args()

    if not 2000 <= args.anio <= 2100 or not 1 <= args.mes <= 12:
        print("Periodo inválido.")
        return 1

    aplicacion = create_app()
    with aplicacion.app_context():
        inicio = datetime(args.anio, args.mes, 1)
        ultimo_dia = calendar.monthrange(args.anio, args.mes)[1]
        fin = datetime(args.anio, args.mes, ultimo_dia, 23, 59, 59)

        if Marca.query.filter(Marca.fecha_hora >= inicio, Marca.fecha_hora <= fin).count():
            print("Ya existen marcas en ese periodo. No se duplicó nada.")
            return 0

        periodo = Periodo.query.filter_by(anio=args.anio, mes=args.mes).first()
        if periodo is None:
            periodo = Periodo(anio=args.anio, mes=args.mes, estado="abierto")
            db.session.add(periodo)
            db.session.commit()
        if periodo.estado != "abierto":
            print(f"El periodo {periodo.etiqueta} está {periodo.estado}.")
            return 0

        lectores = _lectores_por_sede_tipo()
        horarios_por_trabajador: dict[int, dict[int, Horario]] = defaultdict(dict)
        for horario in Horario.query.all():
            horarios_por_trabajador[horario.id_trabajador][horario.dia_semana] = horario

        rng = random.Random(20260000 + args.anio * 100 + args.mes)
        trabajadores = (
            Trabajador.query.filter_by(activo=True).order_by(Trabajador.id_trabajador).all()
        )
        marcas: list[Marca] = []
        dias = [
            date(args.anio, args.mes, dia)
            for dia in range(1, ultimo_dia + 1)
            if date(args.anio, args.mes, dia).weekday() < 5
        ]

        def crear_marca(
            trabajador: Trabajador,
            tipo: str,
            fecha_hora: datetime,
            estado: str,
            incidencia_tipo: str | None = None,
            observacion: str | None = None,
        ) -> None:
            tipo_lector = "entrada" if tipo == "ingreso" else "salida"
            lector = lectores.get((trabajador.area.id_sede, tipo_lector))
            if lector is None:
                lector = next(
                    (item for item in lectores.values() if item.tipo == tipo_lector),
                    None,
                )
            if lector is None:
                return
            marca = Marca(
                fecha_hora=fecha_hora,
                tipo=tipo,
                estado=estado,
                medio="nfc",
                id_trabajador=trabajador.id_trabajador,
                id_lector=lector.id_lector,
                id_sede=lector.id_sede,
            )
            if incidencia_tipo:
                marca.incidencia = Incidencia(
                    tipo=incidencia_tipo,
                    estado="pendiente",
                    observacion=observacion,
                    fecha_creacion=fecha_hora,
                    id_trabajador=trabajador.id_trabajador,
                )
            marcas.append(marca)

        for trabajador in trabajadores:
            for dia in dias:
                horario = horarios_por_trabajador[trabajador.id_trabajador].get(dia.weekday())
                if horario is None:
                    continue
                entrada = datetime.combine(dia, horario.hora_entrada)
                salida = datetime.combine(dia, horario.hora_salida)
                suerte = rng.random()

                if suerte < 0.01:
                    # Salida sin entrada: se registra la salida observada.
                    crear_marca(
                        trabajador,
                        "salida",
                        salida + timedelta(minutes=rng.randint(-8, 10)),
                        "observada",
                        "falta_entrada",
                        "Salida sin un ingreso previo en el día.",
                    )
                elif suerte < 0.02:
                    # Ingreso sin salida: se registra el ingreso y la alerta.
                    crear_marca(
                        trabajador,
                        "ingreso",
                        entrada + timedelta(minutes=rng.randint(-3, 5)),
                        "valida",
                        "falta_salida",
                        "Ingreso sin salida registrada en la jornada.",
                    )
                elif suerte < 0.06:
                    # Tardanza: ingreso observado.
                    minutos = rng.randint(11, 30)
                    crear_marca(
                        trabajador,
                        "ingreso",
                        entrada + timedelta(minutes=minutos),
                        "observada",
                        "fuera_horario",
                        f"Entrada tardía: {minutos} min.",
                    )
                    crear_marca(
                        trabajador,
                        "salida",
                        salida + timedelta(minutes=rng.randint(-5, 10)),
                        "valida",
                    )
                else:
                    crear_marca(
                        trabajador,
                        "ingreso",
                        entrada + timedelta(minutes=rng.randint(-3, 5)),
                        "valida",
                    )
                    crear_marca(
                        trabajador,
                        "salida",
                        salida + timedelta(minutes=rng.randint(-8, 10)),
                        "valida",
                    )

        incidencias_creadas = sum(1 for marca in marcas if marca.incidencia is not None)
        db.session.add_all(marcas)
        db.session.commit()

        print(f"Periodo generado: {periodo.etiqueta}")
        print(f"  Trabajadores: {len(trabajadores)}")
        print(f"  Marcas: {len(marcas)}")
        print(f"  Incidencias: {incidencias_creadas}")
        print("  Abre /preconsolidado para revisar el periodo.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
