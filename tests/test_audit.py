"""Pruebas del visor de auditoría."""

from datetime import datetime

from app.extensions import db
from app.models import Auditoria


def _login(client, correo: str, clave: str):
    return client.post(
        "/login",
        data={"correo": correo, "password": clave},
        follow_redirects=True,
    )


def test_admin_consulta_auditoria(client):
    _login(client, "admin@utsm.edu.pe", "admin123")
    respuesta = client.get("/auditoria")
    assert respuesta.status_code == 200
    assert b"Registro de auditor" in respuesta.data
    assert b"LOGIN" in respuesta.data or b"Inicio de sesi" in respuesta.data


def test_filtro_y_exportacion_auditoria(client):
    _login(client, "admin@utsm.edu.pe", "admin123")
    respuesta = client.get("/auditoria", query_string={"accion": "LOGIN"})
    assert respuesta.status_code == 200
    assert b"Inicio de sesi" in respuesta.data

    exportacion = client.get("/auditoria/exportar.csv", query_string={"accion": "LOGIN"})
    assert exportacion.status_code == 200
    assert exportacion.mimetype == "text/csv"
    assert b"Fecha" in exportacion.data


def test_auditoria_detalle_legible(app, client):
    _login(client, "admin@utsm.edu.pe", "admin123")
    with app.app_context():
        evento = (
            Auditoria.query.filter_by(accion="LOGIN").order_by(Auditoria.id_evento.desc()).first()
        )
        evento_id = evento.id_evento

    respuesta = client.get(f"/auditoria/{evento_id}")
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "Inició sesión" in html
    assert "Cambios registrados" in html
    assert "Detalles técnicos" in html


def test_auditoria_pagina_dos_conserva_filtros(app, client):
    with app.app_context():
        for indice in range(30):
            db.session.add(
                Auditoria(
                    fecha=datetime(2026, 11, 23, 9, 0, indice),
                    accion="LOGIN",
                    tabla_afectada="usuario",
                    registro_id=1,
                    ip="127.0.0.1",
                )
            )
        db.session.commit()

    _login(client, "admin@utsm.edu.pe", "admin123")
    respuesta = client.get("/auditoria", query_string={"accion": "LOGIN", "pagina": 2})
    assert respuesta.status_code == 200
    assert "Página 2 de".encode() in respuesta.data
    assert b"accion=LOGIN" in respuesta.data


def test_trabajador_no_accede_auditoria(client):
    _login(client, "trabajador@utsm.edu.pe", "trabajador123")
    respuesta = client.get("/auditoria")
    assert respuesta.status_code == 403
