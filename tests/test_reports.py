"""Pruebas del preconsolidado, exportaciones y cierre de periodo."""

import csv
import io
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from app.extensions import db
from app.models import (
    Auditoria,
    Consolidado,
    Incidencia,
    Lector,
    Marca,
    Periodo,
    Trabajador,
)
from app.reports.service import construir_resumen, detectar_faltantes, periodo_por_defecto

PERIODO = {"anio": 2026, "mes": 10}
CREDENCIALES = {
    "analista": ("analista@utsm.edu.pe", "analista123"),
    "jefe": ("jefe@utsm.edu.pe", "jefe123"),
    "admin": ("admin@utsm.edu.pe", "admin123"),
}


def _login(client, rol: str):
    correo, clave = CREDENCIALES[rol]
    return client.post(
        "/login",
        data={"correo": correo, "password": clave},
        follow_redirects=True,
    )


def _logout(client):
    return client.post("/logout", follow_redirects=True)


def _lector(tipo: str) -> Lector:
    return Lector.query.filter_by(tipo=tipo, estado="activo").order_by(Lector.id_lector).first()


def _crear_datos(app) -> dict:
    with app.app_context():
        trabajadores = (
            Trabajador.query.filter_by(tipo="admin")
            .order_by(Trabajador.id_trabajador)
            .limit(2)
            .all()
        )
        trabajador_1, trabajador_2 = trabajadores
        entrada = _lector("entrada")
        salida = _lector("salida")

        marca_ingreso = Marca(
            fecha_hora=datetime(2026, 10, 5, 8, 0),
            tipo="ingreso",
            estado="valida",
            medio="nfc",
            id_trabajador=trabajador_1.id_trabajador,
            id_lector=entrada.id_lector,
            id_sede=entrada.id_sede,
        )
        marca_salida = Marca(
            fecha_hora=datetime(2026, 10, 5, 17, 0),
            tipo="salida",
            estado="valida",
            medio="nfc",
            id_trabajador=trabajador_1.id_trabajador,
            id_lector=salida.id_lector,
            id_sede=salida.id_sede,
        )
        marca_incompleta = Marca(
            fecha_hora=datetime(2026, 10, 6, 8, 0),
            tipo="ingreso",
            estado="valida",
            medio="nfc",
            id_trabajador=trabajador_2.id_trabajador,
            id_lector=entrada.id_lector,
            id_sede=entrada.id_sede,
        )
        db.session.add_all([marca_ingreso, marca_salida, marca_incompleta])
        db.session.flush()
        incidencia = Incidencia(
            tipo="falta_salida",
            estado="pendiente",
            observacion="Salida no registrada.",
            fecha_creacion=datetime(2026, 10, 6, 8, 0),
            id_marca=marca_incompleta.id_marca,
            id_trabajador=trabajador_2.id_trabajador,
        )
        db.session.add(incidencia)
        db.session.commit()
        return {
            "trabajador_1": trabajador_1.nombre_corto,
            "dni_1": trabajador_1.dni,
            "trabajador_2": trabajador_2.nombre_corto,
            "incidencia_id": incidencia.id_incidencia,
        }


def test_preconsolidado_calcula_horas_y_excepciones(app, client):
    datos = _crear_datos(app)
    _login(client, "analista")

    respuesta = client.get("/preconsolidado", query_string=PERIODO)
    assert respuesta.status_code == 200
    assert b"Preconsolidado mensual" in respuesta.data
    assert datos["trabajador_1"].encode() in respuesta.data
    assert b"Corregir" in respuesta.data

    with app.app_context():
        resumen = construir_resumen(PERIODO["anio"], PERIODO["mes"])
        assert resumen["total_horas"] == 9.0
        assert resumen["trabajadores_con_marcas"] == 2
        assert resumen["total_excepciones"] == 1
        assert resumen["excepciones"][0].id_incidencia == datos["incidencia_id"]


def test_exportaciones_csv_excel_y_pdf(app, client):
    datos = _crear_datos(app)
    _login(client, "analista")

    csv_resp = client.get("/exportar", query_string={**PERIODO, "formato": "csv"})
    assert csv_resp.status_code == 200
    assert csv_resp.mimetype == "text/csv"
    filas = list(csv.reader(io.StringIO(csv_resp.data.decode("utf-8-sig"))))
    assert filas[0][0] == "Periodo"
    assert any(datos["dni_1"] in fila for fila in filas)

    excel_resp = client.get("/exportar", query_string={**PERIODO, "formato": "excel"})
    assert excel_resp.status_code == 200
    libro = load_workbook(io.BytesIO(excel_resp.data))
    assert {"Resumen", "Incidencias", "Periodo"} <= set(libro.sheetnames)

    pdf_resp = client.get("/exportar", query_string={**PERIODO, "formato": "pdf"})
    assert pdf_resp.status_code == 200
    assert pdf_resp.mimetype == "application/pdf"
    assert pdf_resp.data.startswith(b"%PDF")


def test_analista_corrige_excepcion(app, client):
    datos = _crear_datos(app)
    _login(client, "analista")
    client.get("/preconsolidado", query_string=PERIODO)

    respuesta = client.post(
        f"/preconsolidado/2026/10/excepciones/{datos['incidencia_id']}/corregir",
        data={"nota": "Se verificó con el coordinador del área."},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert b"Excepci" in respuesta.data

    with app.app_context():
        incidencia = db.session.get(Incidencia, datos["incidencia_id"])
        assert incidencia.estado == "cerrada"
        assert Auditoria.query.filter_by(accion="EXCEPCION_CORREGIDA").count() == 1
        assert construir_resumen(2026, 10)["total_excepciones"] == 0


def test_jefe_cierra_periodo_y_bloquea_edicion(app, client):
    datos = _crear_datos(app)
    _login(client, "jefe")

    consulta = client.get("/cierre", query_string=PERIODO)
    assert consulta.status_code == 200
    assert b"Cierre mensual" in consulta.data

    cierre = client.post(
        "/cierre",
        data={**{k: str(v) for k, v in PERIODO.items()}, "confirmar": "1"},
        follow_redirects=True,
    )
    assert cierre.status_code == 200
    assert b"cerrado" in cierre.data.lower()

    with app.app_context():
        periodo = Periodo.query.filter_by(anio=2026, mes=10).first()
        assert periodo is not None
        assert periodo.estado == "cerrado"
        assert periodo.total_horas == 9.0
        assert periodo.total_excepciones == 1
        assert Consolidado.query.filter_by(id_periodo=periodo.id_periodo).count() == 3
        for consolidado in periodo.consolidados:
            assert (Path(app.config["EXPORT_FOLDER"]) / consolidado.archivo).exists()
        assert Auditoria.query.filter_by(accion="PERIODO_CERRADO").count() == 1

    _logout(client)
    _login(client, "analista")
    bloqueado = client.post(
        f"/preconsolidado/2026/10/excepciones/{datos['incidencia_id']}/corregir",
        data={"nota": "Intento posterior al cierre."},
        follow_redirects=True,
    )
    assert bloqueado.status_code == 200
    assert b"cerrado" in bloqueado.data.lower()

    with app.app_context():
        incidencia = db.session.get(Incidencia, datos["incidencia_id"])
        assert incidencia.estado == "pendiente"


def test_solo_el_jefe_cierra_y_se_descarga_archivo(app, client):
    _crear_datos(app)
    _login(client, "analista")
    respuesta = client.post(
        "/cierre",
        data={"anio": "2026", "mes": "10", "confirmar": "1"},
    )
    assert respuesta.status_code == 403

    _logout(client)
    _login(client, "jefe")
    client.post(
        "/cierre",
        data={"anio": "2026", "mes": "10", "confirmar": "1"},
        follow_redirects=True,
    )

    with app.app_context():
        consolidado = Consolidado.query.first()
        assert consolidado is not None
        consolidado_id = consolidado.id_consolidado

    descarga = client.get(f"/consolidados/{consolidado_id}/descargar")
    assert descarga.status_code == 200
    assert len(descarga.data) > 0

    periodos = client.get("/periodos")
    assert periodos.status_code == 200
    assert b"Octubre 2026" in periodos.data


def test_admin_llega_a_periodos_desde_consolidado(app, client):
    _login(client, "admin")
    respuesta = client.get("/consolidado")
    assert respuesta.status_code == 302
    assert "/periodos" in respuesta.headers["Location"]


def test_periodo_por_defecto_prioriza_el_abierto(app):
    with app.app_context():
        db.session.add(Periodo(anio=2026, mes=11, estado="cerrado"))
        db.session.add(Periodo(anio=2026, mes=12, estado="abierto"))
        db.session.commit()
        assert periodo_por_defecto() == (2026, 12)


def test_detectar_faltantes_sin_modificar(app):
    datos = _crear_datos(app)
    with app.app_context():
        faltantes = detectar_faltantes(2026, 10)
        assert any(
            faltante["id_trabajador"] and faltante["tipo"] == "falta_salida"
            for faltante in faltantes
        )
        incidencia = db.session.get(Incidencia, datos["incidencia_id"])
        assert incidencia.estado == "pendiente"
