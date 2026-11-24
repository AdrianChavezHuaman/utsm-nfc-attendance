"""Pruebas del panel KPI y de los endpoints de gráficos."""

CREDENCIALES = {
    "analista": ("analista@utsm.edu.pe", "analista123"),
    "jefe": ("jefe@utsm.edu.pe", "jefe123"),
    "trabajador": ("trabajador@utsm.edu.pe", "trabajador123"),
}


def _login(client, rol: str):
    correo, clave = CREDENCIALES[rol]
    return client.post(
        "/login",
        data={"correo": correo, "password": clave},
        follow_redirects=True,
    )


def test_dashboard_carga_para_analista(client):
    _login(client, "analista")
    respuesta = client.get("/dashboard")
    assert respuesta.status_code == 200
    assert b"Oportunidad del cierre" in respuesta.data
    assert "Eficiencia de consolidación".encode() in respuesta.data
    assert b"Calidad de las marcaciones" in respuesta.data
    assert "La serie 2027 es proyección" in respuesta.get_data(as_text=True)


def test_dashboard_2027_es_proyeccion(client):
    _login(client, "jefe")
    respuesta = client.get("/api/kpi", query_string={"anio": 2027})
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["proyeccion"] is True
    valores = {kpi["clave"]: kpi["valor"] for kpi in datos["kpis"]}
    assert valores == {"oportunidad": 95.0, "eficiencia": 34.0, "calidad": 6.0}


def test_api_chart_historico_y_heatmap(client):
    _login(client, "analista")
    serie = client.get(
        "/api/chart-data",
        query_string={"serie": "historico", "metrica": "calidad", "tipo": "line"},
    )
    assert serie.status_code == 200
    data = serie.get_json()
    assert data["labels"] == ["2024", "2025", "2026", "2027"]
    assert data["datasets"][0]["data"] == [15.0, 13.5, 12.0, 6.0]

    heatmap = client.get(
        "/api/chart-data",
        query_string={"serie": "historico", "tipo": "heatmap"},
    )
    assert heatmap.status_code == 200
    matriz = heatmap.get_json()
    assert len(matriz["y_labels"]) == 3
    assert len(matriz["x_labels"]) == 4


def test_api_operacion_por_area(client):
    _login(client, "analista")
    respuesta = client.get(
        "/api/chart-data",
        query_string={"serie": "operacion", "anio": 2026, "mes": 10, "tipo": "bar"},
    )
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert len(datos["labels"]) == 12
    assert "total_marcas" in datos["meta"]
    assert "nfc_adopcion" in datos["meta"]


def test_operacion_2027_sin_marcas(client):
    _login(client, "analista")
    respuesta = client.get(
        "/api/chart-data",
        query_string={"serie": "operacion", "anio": 2027, "tipo": "bar"},
    )
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["meta"]["total_marcas"] == 0
    assert datos["meta"]["total_incidencias"] == 0


def test_dashboard_solo_roles_rrhh(client):
    _login(client, "trabajador")
    assert client.get("/dashboard").status_code == 403
    assert client.get("/api/kpi").status_code == 403
    assert client.get("/api/chart-data").status_code == 403
