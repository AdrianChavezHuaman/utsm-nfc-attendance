"""Compara la base histórica con los parámetros de la Tabla 9 del v6.

Uso:
    .venv/bin/python scripts/validar_historico.py
    .venv/bin/python scripts/validar_historico.py --anio 2026
    .venv/bin/python scripts/validar_historico.py --estricto

El script no modifica datos. Sirve para revisar la correlación entre las marcas
sembradas y las tasas de calidad de 2024-2026, además del escenario simulado de
enero 2027, antes de actualizar el documento.
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy import case, func

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Incidencia, Marca, Periodo  # noqa: E402
from seeds.seed_historico import TASAS_CALIDAD  # noqa: E402

TOLERANCIA = 0.5


def _filas(anio: int | None) -> list[dict]:
    consulta = (
        db.session.query(
            func.strftime("%Y", Marca.fecha_hora).label("anio"),
            func.strftime("%m", Marca.fecha_hora).label("mes"),
            func.count(Marca.id_marca).label("marcas"),
            func.sum(case((Marca.medio == "nfc", 1), else_=0)).label("nfc"),
        )
        .group_by("anio", "mes")
        .order_by("anio", "mes")
    )
    if anio:
        consulta = consulta.filter(func.strftime("%Y", Marca.fecha_hora) == str(anio))

    incidencias = {
        (fila[0], fila[1]): int(fila[2])
        for fila in db.session.query(
            func.strftime("%Y", Marca.fecha_hora),
            func.strftime("%m", Marca.fecha_hora),
            func.count(Incidencia.id_incidencia),
        )
        .join(Incidencia, Incidencia.id_marca == Marca.id_marca)
        .group_by(func.strftime("%Y", Marca.fecha_hora), func.strftime("%m", Marca.fecha_hora))
        .all()
    }
    periodos = {(periodo.anio, periodo.mes): periodo for periodo in Periodo.query.all()}

    filas = []
    for fila in consulta:
        clave = (int(fila.anio), int(fila.mes))
        total = int(fila.marcas)
        incidentes = int(incidencias.get((fila.anio, fila.mes), 0))
        calidad = round(incidentes / total * 100, 2) if total else 0.0
        nfc = round(int(fila.nfc or 0) / total * 100, 1) if total else 0.0
        periodo = periodos.get(clave)
        esperado = TASAS_CALIDAD.get(clave[0], 0) * 100
        estado = periodo.estado if periodo else "sin periodo"
        if periodo and periodo.es_simulacion:
            estado = "simulado"
        filas.append(
            {
                "anio": clave[0],
                "mes": clave[1],
                "marcas": total,
                "incidencias": incidentes,
                "calidad": calidad,
                "esperado": esperado,
                "desviacion": round(calidad - esperado, 2),
                "nfc": nfc,
                "estado": estado,
            }
        )
    return filas


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida la correlación histórica con la Tabla 9.")
    parser.add_argument("--anio", type=int, help="Limita la revisión a un año.")
    parser.add_argument(
        "--estricto",
        action="store_true",
        help="Devuelve error si algún mes se aleja más de 0.5 puntos del parámetro.",
    )
    args = parser.parse_args()

    aplicacion = create_app()
    with aplicacion.app_context():
        filas = _filas(args.anio)
        if not filas:
            print("No hay marcas históricas en la base.")
            return 1

        print("AÑO-MES   MARCAS   INCID.  CALIDAD  ESPERADO  DELTA   NFC   PERIODO")
        print("-------------------------------------------------------------------")
        desviados = []
        for fila in filas:
            print(
                f"{fila['anio']}-{fila['mes']:02d}  "
                f"{fila['marcas']:>7,}  {fila['incidencias']:>6,}  "
                f"{fila['calidad']:>6.2f}  {fila['esperado']:>7.2f}  "
                f"{fila['desviacion']:>+6.2f}  {fila['nfc']:>5.1f}  {fila['estado']}"
            )
            if abs(fila["desviacion"]) > TOLERANCIA:
                desviados.append(fila)

        print("\nResumen anual:")
        for anio in sorted({fila["anio"] for fila in filas}):
            del_anio = [fila for fila in filas if fila["anio"] == anio]
            marcas = sum(fila["marcas"] for fila in del_anio)
            incidencias = sum(fila["incidencias"] for fila in del_anio)
            calidad = incidencias / marcas * 100 if marcas else 0
            nfc = sum(fila["nfc"] * fila["marcas"] for fila in del_anio) / marcas if marcas else 0
            esperado = TASAS_CALIDAD.get(anio, 0) * 100
            print(
                f"  {anio}: {marcas:>8,} marcas · {incidencias:>7,} incidencias · "
                f"calidad {calidad:>5.2f} % (Tabla 9: {esperado:g} %) · NFC {nfc:>5.1f} %"
            )

        if any(fila["estado"] == "simulado" for fila in filas):
            print("\nNota: enero 2027 es un escenario TO-BE simulado, no una medición real.")

        if desviados:
            print("\nMeses fuera de ±0.5 puntos:")
            for fila in desviados:
                print(
                    f"  {fila['anio']}-{fila['mes']:02d}: {fila['calidad']:.2f} % "
                    f"frente a {fila['esperado']:.2f} %"
                )
            print(
                "  Nota: revisa los meses marcados frente a la Tabla 9 antes de "
                "actualizar el documento."
            )
            if args.estricto:
                return 2

        print("\nValidación completada.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
