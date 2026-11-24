"""Pruebas del consolidado anual y sus comparativas."""

from app.reports.annual import construir_anual
from seeds.seed_historico import generar_historico

CREDENCIALES = {
    "admin": ("admin@utsm.edu.pe", "admin123"),
    "analista": ("analista@utsm.edu.pe", "analista123"),
    "trabajador": ("trabajador@utsm.edu.pe", "trabajador123"),
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


def test_consolidado_anual_carga_y_muestra_comparativas(app, client):
    _login(client, "admin")
    respuesta = client.get("/consolidado-anual", query_string={"anio": 2026})
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "Consolidado anual 2026" in html
    assert "Matriz mensual" in html
    assert "Enero vs enero" in html
    assert "Año vs año" in html
    assert "Diciembre 2026" in html


def test_consolidado_anual_2027_es_simulado(app, client):
    _login(client, "analista")
    respuesta = client.get("/consolidado-anual", query_string={"anio": 2027})
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "TO-BE simulado" in html
    assert "Sin datos" in html
    assert "6.0 %" in html
    assert "2027 anual es la meta TO-BE" in html


def test_consolidado_anual_filtros_y_permisos(app, client):
    _login(client, "admin")
    respuesta = client.get(
        "/consolidado-anual",
        query_string={"anio": 2026, "tipo": "docente_tp"},
    )
    assert respuesta.status_code == 200
    assert "Filtros operativos activos" in respuesta.get_data(as_text=True)
    _logout(client)

    _login(client, "trabajador")
    assert client.get("/consolidado-anual").status_code == 403


def test_consolidado_anual_exporta_csv_excel_pdf(app, client):
    _login(client, "admin")
    csv = client.get(
        "/consolidado-anual/exportar",
        query_string={"formato": "csv", "anio": 2026},
    )
    assert csv.status_code == 200
    assert csv.mimetype == "text/csv"
    assert "Consolidado anual UTSM" in csv.get_data(as_text=True)

    excel = client.get(
        "/consolidado-anual/exportar",
        query_string={"formato": "excel", "anio": 2026},
    )
    assert excel.status_code == 200
    assert "spreadsheetml" in excel.content_type
    assert len(excel.data) > 1000

    pdf = client.get(
        "/consolidado-anual/exportar",
        query_string={"formato": "pdf", "anio": 2026},
    )
    assert pdf.status_code == 200
    assert pdf.mimetype == "application/pdf"
    assert pdf.data.startswith(b"%PDF")


def test_reporte_anual_calcula_mes_y_enero(app, db_session):
    generar_historico(
        anios=[2026],
        meses=[1],
        objetivo_mensual=100,
        limite_trabajadores=10,
        limite_dias=3,
    )
    datos = construir_anual(2026)
    assert datos["resumen"]["total_marcas"] == 100
    assert datos["meses"][0]["marcas"] == 100
    assert datos["meses"][1]["marcas"] == 0
    assert datos["eneros"][2]["anio"] == 2026
    assert datos["eneros"][2]["marcas"] == 100
    assert datos["comparativa"][2]["anio"] == 2026
    assert datos["comparativa"][2]["marcas"] == 100


def test_vista_semestral_agrupa_seis_meses(app, db_session):
    generar_historico(
        anios=[2026],
        meses=list(range(1, 13)),
        objetivo_mensual=100,
        limite_trabajadores=10,
        limite_dias=3,
    )
    anual = construir_anual(2026)
    primero = construir_anual(2026, vista="s1")
    segundo = construir_anual(2026, vista="s2")

    assert len(primero["meses"]) == 6
    assert primero["meses"][0]["mes"] == 1
    assert primero["meses"][-1]["mes"] == 6
    assert segundo["meses"][0]["mes"] == 7
    assert segundo["meses"][-1]["mes"] == 12

    assert primero["vista_codigo"] == "S1"
    assert primero["vista_rango"] == "Enero – junio"
    assert (
        primero["resumen"]["total_marcas"] + segundo["resumen"]["total_marcas"]
        == anual["resumen"]["total_marcas"]
    )
    assert (
        primero["resumen"]["total_incidencias"] + segundo["resumen"]["total_incidencias"]
        == anual["resumen"]["total_incidencias"]
    )


def test_vista_invalida_vuelve_a_anual(app, db_session):
    datos = construir_anual(2026, vista="trimestre")
    assert datos["vista"] == "anual"
    assert len(datos["meses"]) == 12


def test_vista_semestral_en_pantalla_y_exportacion(app, client):
    _login(client, "admin")
    respuesta = client.get(
        "/consolidado-anual",
        query_string={"anio": 2026, "vista": "s1"},
    )
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "Consolidado S1 2026" in html
    assert "Primer semestre" in html
    assert "Junio 2026" in html
    assert "Julio 2026" not in html
    assert "Enero vs enero" not in html
    assert "está disponible en la vista anual" in html

    csv = client.get(
        "/consolidado-anual/exportar",
        query_string={"formato": "csv", "anio": 2026, "vista": "s1"},
    )
    texto = csv.get_data(as_text=True)
    assert csv.status_code == 200
    assert "Consolidado S1 UTSM" in texto
    assert "Comparación enero" not in texto

    excel = client.get(
        "/consolidado-anual/exportar",
        query_string={"formato": "excel", "anio": 2026, "vista": "s2"},
    )
    assert excel.status_code == 200
    from io import BytesIO

    from openpyxl import load_workbook

    libro = load_workbook(BytesIO(excel.data))
    assert libro.sheetnames == ["Mensual"]

    pdf = client.get(
        "/consolidado-anual/exportar",
        query_string={"formato": "pdf", "anio": 2026, "vista": "s1"},
    )
    assert pdf.status_code == 200
    assert pdf.data.startswith(b"%PDF")
