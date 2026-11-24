"""Pruebas del seed histórico 2024-2026 y su correlación básica."""

import pytest

from app.models import Incidencia, IndicadorPeriodo, Marca, Periodo, Trabajador
from app.reports.service import calcular_horas_trabajador
from seeds.seed_historico import generar_historico

OBJETIVO = 100
PARAMETROS = {
    "anios": [2026],
    "meses": [1],
    "objetivo_mensual": OBJETIVO,
    "limite_trabajadores": 10,
    "limite_dias": 3,
}


def test_genera_un_mes_con_volumen_y_calidad_objetivo(app, db_session):
    resumen = generar_historico(**PARAMETROS)

    assert Marca.query.count() == OBJETIVO
    assert Incidencia.query.count() == 12
    assert resumen["generados"][0]["tasa"] == 12.0
    assert resumen["generados"][0]["trabajadores"] == 10

    tipos = {incidencia.tipo for incidencia in Incidencia.query.all()}
    assert {"falta_entrada", "falta_salida", "fuera_horario"} <= tipos


def test_periodo_cerrado_y_horas_coherentes(app, db_session):
    generar_historico(**PARAMETROS)
    periodo = Periodo.query.filter_by(anio=2026, mes=1).one()

    assert periodo.estado == "cerrado"
    assert periodo.fecha_cierre is not None
    assert periodo.total_trabajadores == 10
    assert periodo.total_incidencias == 12
    assert periodo.total_excepciones == 0

    total = sum(
        calcular_horas_trabajador(trabajador, 2026, 1) for trabajador in Trabajador.query.all()
    )
    assert abs(periodo.total_horas - total) <= 0.05


def test_seed_es_idempotente_y_reemplaza_si_se_pide(app, db_session):
    generar_historico(**PARAMETROS)
    marcas_iniciales = Marca.query.count()

    segundo = generar_historico(**PARAMETROS)
    assert segundo["generados"] == []
    assert segundo["omitidos"] == ["2026-01"]
    assert Marca.query.count() == marcas_iniciales

    tercero = generar_historico(**PARAMETROS, reemplazar=True)
    assert len(tercero["generados"]) == 1
    assert Marca.query.count() == OBJETIVO
    assert Incidencia.query.count() == 12


def test_2024_es_as_is_sin_nfc_y_rechaza_anios_fuera_de_rango(app, db_session):
    generar_historico(
        anios=[2024],
        meses=[3],
        objetivo_mensual=120,
        limite_trabajadores=10,
        limite_dias=4,
    )
    assert Marca.query.filter_by(medio="nfc").count() == 0
    assert Marca.query.filter_by(medio="huella").count() == 120

    with pytest.raises(ValueError, match="2028"):
        generar_historico(anios=[2028], meses=[1])


def test_enero_2027_es_escenario_to_be_simulado(app, db_session):
    resumen = generar_historico(
        anios=[2027],
        objetivo_mensual=OBJETIVO,
        limite_trabajadores=10,
        limite_dias=3,
    )
    periodo = Periodo.query.filter_by(anio=2027, mes=1).one()
    indicador = IndicadorPeriodo.query.filter_by(anio=2027, mes=1, escenario="to_be_simulado").one()

    assert periodo.estado == "cerrado"
    assert periodo.escenario == "to_be_simulado"
    assert Incidencia.query.count() == 6
    assert resumen["generados"][0]["nfc"] >= 80
    assert indicador.calidad_pct == 6.0
    assert indicador.adopcion_nfc == 95.0


def test_diciembre_2026_queda_abierto_para_el_cierre(app, db_session):
    generar_historico(
        anios=[2026],
        meses=[12],
        objetivo_mensual=OBJETIVO,
        limite_trabajadores=10,
        limite_dias=3,
    )
    periodo = Periodo.query.filter_by(anio=2026, mes=12).one()
    assert periodo.estado == "abierto"
    assert periodo.total_excepciones == 12
    assert Incidencia.query.filter_by(estado="pendiente").count() == 12


def test_limpieza_de_periodos_vacios(app, db_session):
    db_session.add(Periodo(anio=2027, mes=1, estado="abierto"))
    db_session.commit()

    generar_historico(**PARAMETROS)

    assert Periodo.query.filter_by(anio=2027, mes=1).first() is None
