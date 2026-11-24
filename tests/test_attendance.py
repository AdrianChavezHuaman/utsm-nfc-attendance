"""Pruebas de asistencia diaria, personal y horarios semanales."""

from datetime import date, datetime, time

from app.extensions import db
from app.models import (
    Auditoria,
    Horario,
    Incidencia,
    Lector,
    Marca,
    Periodo,
    Trabajador,
    Usuario,
)

FECHA = date(2026, 11, 23)
CREDENCIALES = {
    "admin": ("admin@utsm.edu.pe", "admin123"),
    "jefe": ("jefe@utsm.edu.pe", "jefe123"),
    "analista": ("analista@utsm.edu.pe", "analista123"),
    "coordinador": ("coordinador@utsm.edu.pe", "coordinador123"),
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


def _trabajador_con_horario(dia: int = 0, hora: time = time(8, 0)):
    return (
        Trabajador.query.join(Horario)
        .filter(
            Trabajador.tipo == "admin",
            Horario.dia_semana == dia,
            Horario.hora_entrada == hora,
        )
        .order_by(Trabajador.id_trabajador)
        .first()
    )


def test_asistencia_admin_carga_y_muestra_trabajadores(app, client):
    _login(client, "admin")
    respuesta = client.get("/asistencia", query_string={"fecha": FECHA.isoformat()})
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "Asistencia del personal" in html
    assert "Con presencia" in html
    assert "Alonso Herrera" in html


def test_asistencia_muestra_presente_con_marcas(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        sede_id = trabajador.area.id_sede
        entrada = Lector.query.filter_by(id_sede=sede_id, tipo="entrada").first()
        salida = Lector.query.filter_by(id_sede=sede_id, tipo="salida").first()
        db.session.add(
            Marca(
                fecha_hora=datetime.combine(FECHA, time(8, 5)),
                tipo="ingreso",
                estado="valida",
                medio="huella",
                id_trabajador=trabajador.id_trabajador,
                id_lector=entrada.id_lector,
                id_sede=sede_id,
            )
        )
        db.session.add(
            Marca(
                fecha_hora=datetime.combine(FECHA, time(17, 5)),
                tipo="salida",
                estado="valida",
                medio="huella",
                id_trabajador=trabajador.id_trabajador,
                id_lector=salida.id_lector,
                id_sede=sede_id,
            )
        )
        db.session.commit()
        dni = trabajador.dni

    _login(client, "admin")
    respuesta = client.get(
        "/asistencia",
        query_string={"fecha": FECHA.isoformat(), "q": dni},
    )
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "Presente" in html
    assert "08:05" in html
    assert "17:05" in html


def test_coordinador_solo_ve_su_area(app, client):
    _login(client, "coordinador")
    respuesta = client.get("/asistencia", query_string={"fecha": FECHA.isoformat()})
    html = respuesta.get_data(as_text=True)
    assert respuesta.status_code == 200
    assert "Solo Escuela de Administración" in html
    assert "Rectorado" not in html


def test_trabajador_redirige_a_su_ficha_y_no_entra_a_asistencia(app, client):
    _login(client, "trabajador")
    assert client.get("/asistencia", query_string={"fecha": FECHA.isoformat()}).status_code == 403
    respuesta = client.get("/mi-asistencia")
    assert respuesta.status_code == 302
    assert "/personal/" in respuesta.headers["Location"]


def test_personal_y_permisos_por_rol(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        trabajador_id = trabajador.id_trabajador
        area_coordinador = (
            Usuario.query.filter_by(correo="coordinador@utsm.edu.pe").first().trabajador.area
        )
        propio_id = (
            Usuario.query.filter_by(correo="trabajador@utsm.edu.pe")
            .first()
            .trabajador.id_trabajador
        )
        otro_area = (
            Trabajador.query.filter(Trabajador.id_area != area_coordinador.id_area)
            .order_by(Trabajador.id_trabajador)
            .first()
        )
        otro_area_id = otro_area.id_trabajador

    _login(client, "admin")
    assert client.get("/personal").status_code == 200
    assert client.get(f"/personal/{trabajador_id}").status_code == 200
    assert client.get(f"/personal/{trabajador_id}?vista=lista").status_code == 200
    _logout(client)

    _login(client, "coordinador")
    assert client.get(f"/personal/{trabajador_id}").status_code == 403
    assert client.get(f"/personal/{propio_id}").status_code == 200
    assert client.get(f"/personal/{otro_area_id}").status_code == 403
    assert client.get("/personal").status_code == 200
    _logout(client)

    _login(client, "trabajador")
    assert client.get("/personal").status_code == 403
    assert client.get(f"/personal/{propio_id}").status_code == 200
    assert client.get(f"/personal/{trabajador_id}").status_code == 403


def test_horarios_admin_agrupados_y_edicion_semanal(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        trabajador_id = trabajador.id_trabajador
        dni = trabajador.dni

    _login(client, "admin")
    listado = client.get("/admin/horarios")
    html = listado.get_data(as_text=True)
    assert listado.status_code == 200
    assert "Semana por trabajador" in html
    assert html.count("Alonso Herrera") == 1

    formulario = client.get(f"/admin/horarios/{trabajador_id}/semana")
    assert formulario.status_code == 200
    assert "Semana laboral" in formulario.get_data(as_text=True)

    datos = {}
    for dia in range(5):
        datos[f"dia_{dia}_activo"] = "1"
        datos[f"dia_{dia}_entrada"] = "09:00"
        datos[f"dia_{dia}_salida"] = "18:00"
        datos[f"dia_{dia}_turno"] = "completo"
    respuesta = client.post(
        f"/admin/horarios/{trabajador_id}/semana",
        data=datos,
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    with app.app_context():
        horario = Horario.query.filter_by(id_trabajador=trabajador_id, dia_semana=0).one()
        assert horario.hora_entrada == time(9, 0)
        assert horario.hora_salida == time(18, 0)
        assert Auditoria.query.filter_by(accion="HORARIO_ACTUALIZADO").count() == 1
        assert dni


def test_kiosko_misma_pestana_y_volver(app, client):
    _login(client, "admin")
    inicio = client.get("/inicio").get_data(as_text=True)
    kiosco = client.get("/kiosk").get_data(as_text=True)
    assert "Kiosco NFC" in inicio
    assert 'target="_blank"' not in inicio
    assert "Volver al panel" in kiosco


# ---------------------------------------------------------------------------
# Corrección manual de marcaciones (Fase 8)
# ---------------------------------------------------------------------------


def _marca_de(trabajador, tipo="ingreso", hora=time(8, 5), fecha=FECHA):
    sede_id = trabajador.area.id_sede
    lector = Lector.query.filter_by(
        id_sede=sede_id, tipo="entrada" if tipo == "ingreso" else "salida"
    ).first()
    marca = Marca(
        fecha_hora=datetime.combine(fecha, hora),
        tipo=tipo,
        estado="valida",
        medio="huella",
        id_trabajador=trabajador.id_trabajador,
        id_lector=lector.id_lector,
        id_sede=sede_id,
    )
    db.session.add(marca)
    db.session.commit()
    return marca


def test_admin_corrige_marca_con_motivo_y_auditoria(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        marca = _marca_de(trabajador)
        trabajador_id = trabajador.id_trabajador
        marca_id = marca.id_marca

    _login(client, "admin")
    listado = client.get(f"/personal/{trabajador_id}/marcas?anio=2026&mes=11")
    assert listado.status_code == 200
    assert "Corregir" in listado.get_data(as_text=True)

    respuesta = client.post(
        f"/personal/{trabajador_id}/marcas/{marca_id}/corregir",
        data={
            "fecha": "23/11/2026",
            "hora": "08:02",
            "tipo": "ingreso",
            "motivo": "El lector registró la hora con retraso.",
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert "corregida" in respuesta.get_data(as_text=True).lower()

    with app.app_context():
        actual = db.session.get(Marca, marca_id)
        assert actual.fecha_hora == datetime(2026, 11, 23, 8, 2)
        evento = Auditoria.query.filter_by(accion="CORREGIR_MARCA").first()
        assert evento is not None
        assert "08:05" in evento.valores_anteriores
        assert "08:02" in evento.valores_nuevos
        assert "retraso" in evento.valores_nuevos


def test_correccion_exige_motivo_suficiente(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        marca = _marca_de(trabajador)
        trabajador_id = trabajador.id_trabajador
        marca_id = marca.id_marca

    _login(client, "analista")
    respuesta = client.post(
        f"/personal/{trabajador_id}/marcas/{marca_id}/corregir",
        data={"fecha": "23/11/2026", "hora": "08:02", "tipo": "ingreso", "motivo": "corto"},
    )
    assert respuesta.status_code == 200
    assert "entre 8 y 280" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Marca, marca_id).fecha_hora == datetime(2026, 11, 23, 8, 5)


def test_correccion_bloqueada_en_periodo_cerrado(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        marca = _marca_de(trabajador)
        db.session.add(Periodo(anio=2026, mes=11, estado="cerrado"))
        db.session.commit()
        trabajador_id = trabajador.id_trabajador
        marca_id = marca.id_marca

    _login(client, "admin")
    listado = client.get(f"/personal/{trabajador_id}/marcas?anio=2026&mes=11")
    assert "Periodo cerrado" in listado.get_data(as_text=True)

    respuesta = client.post(
        f"/personal/{trabajador_id}/marcas/{marca_id}/corregir",
        data={
            "fecha": "23/11/2026",
            "hora": "08:02",
            "tipo": "ingreso",
            "motivo": "Intento sobre un periodo cerrado.",
        },
        follow_redirects=True,
    )
    assert "no admite correcciones" in respuesta.get_data(as_text=True)

    with app.app_context():
        assert db.session.get(Marca, marca_id).fecha_hora == datetime(2026, 11, 23, 8, 5)


def test_correccion_solo_para_roles_de_rrhh(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        marca = _marca_de(trabajador)
        trabajador_id = trabajador.id_trabajador
        marca_id = marca.id_marca

    for rol in ("coordinador", "trabajador"):
        _login(client, rol)
        assert client.get(f"/personal/{trabajador_id}/marcas").status_code == 403
        assert (
            client.post(
                f"/personal/{trabajador_id}/marcas/{marca_id}/corregir",
                data={
                    "fecha": "23/11/2026",
                    "hora": "08:02",
                    "tipo": "ingreso",
                    "motivo": "Sin permiso para corregir.",
                },
            ).status_code
            == 403
        )
        _logout(client)


def test_correccion_cierra_la_incidencia_pendiente(app, client):
    with app.app_context():
        trabajador = _trabajador_con_horario()
        marca = _marca_de(trabajador)
        db.session.add(
            Incidencia(
                tipo="fuera_horario",
                estado="pendiente",
                observacion="Marcación fuera del horario.",
                id_marca=marca.id_marca,
                id_trabajador=trabajador.id_trabajador,
            )
        )
        db.session.commit()
        trabajador_id = trabajador.id_trabajador
        marca_id = marca.id_marca

    _login(client, "jefe")
    respuesta = client.post(
        f"/personal/{trabajador_id}/marcas/{marca_id}/corregir",
        data={
            "fecha": "23/11/2026",
            "hora": "08:00",
            "tipo": "ingreso",
            "motivo": "La marcación se registró fuera de rango.",
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200

    with app.app_context():
        incidencia = Incidencia.query.filter_by(id_marca=marca_id).first()
        assert incidencia.estado == "cerrada"
        assert "Corrección manual" in incidencia.observacion
