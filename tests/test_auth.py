"""Pruebas del flujo de autenticación y auditoría."""

from datetime import datetime, timedelta

import pytest

from app.auth.policy import errores_password
from app.models import Auditoria, Usuario

CREDENCIALES = [
    ("admin@utsm.edu.pe", "admin123", "Administrador"),
    ("jefe@utsm.edu.pe", "jefe123", "Jefe de RR. HH."),
    ("analista@utsm.edu.pe", "analista123", "Analista de RR. HH."),
    ("coordinador@utsm.edu.pe", "coordinador123", "Coordinador de área"),
    ("trabajador@utsm.edu.pe", "trabajador123", "Trabajador"),
]


def test_login_page_carga(client):
    respuesta = client.get("/login")
    assert respuesta.status_code == 200
    assert b"Control de Asistencia" in respuesta.data
    assert b"Credenciales de demostraci" in respuesta.data


def test_inicio_requiere_sesion(client):
    respuesta = client.get("/inicio")
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_raiz_redirige_a_login(client):
    respuesta = client.get("/")
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


@pytest.mark.parametrize("correo,clave,rol_visible", CREDENCIALES)
def test_login_de_los_cinco_roles(client, app, correo, clave, rol_visible):
    respuesta = client.post(
        "/login",
        data={"correo": correo, "password": clave},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert rol_visible.encode() in respuesta.data
    assert b"Prototipo operativo" in respuesta.data

    with app.app_context():
        evento = (
            Auditoria.query.filter_by(accion="LOGIN").order_by(Auditoria.id_evento.desc()).first()
        )
        assert evento is not None
        assert evento.ip is not None


def test_login_con_password_incorrecta(client, app):
    respuesta = client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "incorrecta"},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    assert b"Credenciales inv" in respuesta.data

    with app.app_context():
        evento = Auditoria.query.filter_by(accion="LOGIN_FALLIDO").first()
        assert evento is not None
        # El correo existe: se vincula el intento a la cuenta objetivo.
        assert evento.id_usuario is not None


def test_login_email_desconocido(client, app):
    respuesta = client.post(
        "/login",
        data={"correo": "nadie@utsm.edu.pe", "password": "x"},
        follow_redirects=True,
    )
    assert b"Credenciales inv" in respuesta.data
    with app.app_context():
        evento = Auditoria.query.filter_by(accion="LOGIN_FALLIDO").first()
        assert evento is not None
        assert evento.id_usuario is None


def test_login_no_permite_redireccion_externa(client):
    respuesta = client.post(
        "/login?next=//evil.example.com",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/inicio"


def test_login_permite_next_relativo(client):
    respuesta = client.post(
        "/login?next=/inicio",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/inicio"


def test_logout_registra_auditoria(client, app):
    client.post("/login", data={"correo": "admin@utsm.edu.pe", "password": "admin123"})
    respuesta = client.post("/logout", follow_redirects=True)
    assert respuesta.status_code == 200
    assert b"Sesi" in respuesta.data

    with app.app_context():
        assert Auditoria.query.filter_by(accion="LOGOUT").count() == 1


def test_usuario_anonimo_recibe_404_estilizado(client):
    respuesta = client.get("/ruta-que-no-existe")
    assert respuesta.status_code == 404
    assert b"P\xc3\xa1gina no encontrada" in respuesta.data


def test_roles_required_controla_el_acceso(app, client):
    from app.utils.decorators import roles_required

    @app.route("/solo-jefe")
    @roles_required("jefe")
    def solo_jefe():
        return "panel exclusivo de jefatura"

    cliente = client
    cliente.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    respuesta = cliente.get("/solo-jefe")
    assert respuesta.status_code == 403
    assert b"Acceso denegado" in respuesta.data

    cliente.post("/logout")
    cliente.post(
        "/login",
        data={"correo": "jefe@utsm.edu.pe", "password": "jefe123"},
    )
    respuesta = cliente.get("/solo-jefe")
    assert respuesta.status_code == 200
    assert b"panel exclusivo de jefatura" in respuesta.data


def test_usuario_inactivo_no_puede_ingresar(client, app):
    from app.extensions import db
    from app.models import Usuario

    with app.app_context():
        usuario = Usuario.query.filter_by(correo="analista@utsm.edu.pe").first()
        usuario.activo = False
        db.session.commit()

    respuesta = client.post(
        "/login",
        data={"correo": "analista@utsm.edu.pe", "password": "analista123"},
        follow_redirects=True,
    )
    assert b"Credenciales inv" in respuesta.data

    with app.app_context():
        evento = Auditoria.query.filter_by(accion="LOGIN_FALLIDO").first()
        assert evento is not None
        assert evento.id_usuario is not None


# ---------------------------------------------------------------------------
# Seguridad de acceso (Fase 7)
# ---------------------------------------------------------------------------


def test_bloqueo_tras_cinco_intentos(client, app):
    for _ in range(5):
        client.post(
            "/login",
            data={"correo": "admin@utsm.edu.pe", "password": "incorrecta"},
        )

    respuesta = client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
        follow_redirects=True,
    )
    assert b"Credenciales inv" in respuesta.data

    with app.app_context():
        usuario = Usuario.query.filter_by(correo="admin@utsm.edu.pe").first()
        assert usuario.intentos_fallidos == 5
        assert usuario.bloqueado_hasta is not None
        evento = Auditoria.query.filter_by(accion="LOGIN_BLOQUEADO").first()
        assert evento is not None


def test_bloqueo_expira_y_permite_ingresar(client, app):
    with app.app_context():
        from app.extensions import db

        usuario = Usuario.query.filter_by(correo="admin@utsm.edu.pe").first()
        usuario.intentos_fallidos = 5
        usuario.bloqueado_hasta = datetime.now() - timedelta(minutes=1)
        db.session.commit()

    respuesta = client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    assert respuesta.status_code == 302
    assert respuesta.headers["Location"] == "/inicio"

    with app.app_context():
        usuario = Usuario.query.filter_by(correo="admin@utsm.edu.pe").first()
        assert usuario.intentos_fallidos == 0
        assert usuario.bloqueado_hasta is None


def test_login_correcto_reinicia_intentos(client, app):
    with app.app_context():
        from app.extensions import db

        usuario = Usuario.query.filter_by(correo="jefe@utsm.edu.pe").first()
        usuario.intentos_fallidos = 3
        db.session.commit()

    client.post(
        "/login",
        data={"correo": "jefe@utsm.edu.pe", "password": "jefe123"},
    )

    with app.app_context():
        usuario = Usuario.query.filter_by(correo="jefe@utsm.edu.pe").first()
        assert usuario.intentos_fallidos == 0


def test_mensaje_de_bloqueo_no_revela_la_cuenta(client, app):
    for _ in range(5):
        client.post(
            "/login",
            data={"correo": "admin@utsm.edu.pe", "password": "incorrecta"},
        )
    bloqueado = client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
        follow_redirects=True,
    )
    inexistente = client.post(
        "/login",
        data={"correo": "nadie@utsm.edu.pe", "password": "incorrecta"},
        follow_redirects=True,
    )
    assert b"Credenciales inv" in bloqueado.data
    assert b"Credenciales inv" in inexistente.data


def test_sesion_expira_por_inactividad(client):
    client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    with client.session_transaction() as sesion:
        sesion["ultimo_movimiento"] = (datetime.now() - timedelta(minutes=31)).isoformat()

    respuesta = client.get("/inicio")
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]

    with client.session_transaction() as sesion:
        assert "_user_id" not in sesion


def test_cabeceras_de_seguridad_en_pagina_privada(client):
    client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    respuesta = client.get("/inicio")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert respuesta.headers["Referrer-Policy"] == "same-origin"
    assert "no-store" in respuesta.headers["Cache-Control"]


def test_login_publico_tiene_cabeceras_basicas(client):
    respuesta = client.get("/login")
    assert respuesta.headers["X-Content-Type-Options"] == "nosniff"
    assert respuesta.headers["X-Frame-Options"] == "SAMEORIGIN"


@pytest.mark.parametrize(
    "password,valido",
    [
        ("Clave2026", True),
        ("clave2026", True),
        ("12345678", False),
        ("clave", False),
        ("clave con espacio1", False),
    ],
)
def test_politica_de_password(password, valido):
    assert bool(errores_password(password)) is not valido


def test_admin_rechaza_password_debil(client, app):
    client.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    respuesta = client.post(
        "/admin/usuarios/nuevo",
        data={
            "correo": "nuevo@utsm.edu.pe",
            "rol": "trabajador",
            "activo": "y",
            "password": "debil",
        },
    )
    assert respuesta.status_code == 200
    assert "Incluye al menos un número".encode() in respuesta.data

    with app.app_context():
        assert Usuario.query.filter_by(correo="nuevo@utsm.edu.pe").first() is None
