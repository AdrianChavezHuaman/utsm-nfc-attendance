"""Pruebas de administración de catálogos y usuarios."""

from app.extensions import db
from app.models import (
    Auditoria,
    Lector,
    Sede,
    Tarjeta,
    Trabajador,
    Usuario,
)


def _login(client, correo: str = "admin@utsm.edu.pe", clave: str = "admin123"):
    return client.post(
        "/login",
        data={"correo": correo, "password": clave},
        follow_redirects=True,
    )


def test_admin_carga_y_listados(client):
    _login(client)
    for ruta in (
        "/admin",
        "/admin/sedes",
        "/admin/areas",
        "/admin/trabajadores",
        "/admin/tarjetas",
        "/admin/horarios",
        "/admin/lectores",
        "/admin/usuarios",
        "/admin/reglas",
    ):
        respuesta = client.get(ruta)
        assert respuesta.status_code == 200, ruta


def test_admin_crea_y_edita_sede(app, client):
    _login(client)
    respuesta = client.post(
        "/admin/sedes/nuevo",
        data={"nombre": "Sede Prueba", "direccion": "Av. Prueba 100", "activa": "1"},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    with app.app_context():
        sede = Sede.query.filter_by(nombre="Sede Prueba").first()
        assert sede is not None
        sede_id = sede.id_sede
        assert Auditoria.query.filter_by(accion="ADMIN_CREAR").count() >= 1

    client.post(
        f"/admin/sedes/{sede_id}/editar",
        data={"nombre": "Sede Prueba Editada", "direccion": "Av. Prueba 200", "activa": "1"},
        follow_redirects=True,
    )
    with app.app_context():
        sede = db.session.get(Sede, sede_id)
        assert sede.nombre == "Sede Prueba Editada"
        assert Auditoria.query.filter_by(accion="ADMIN_EDITAR").count() >= 1


def test_admin_bloquea_tarjeta(app, client):
    with app.app_context():
        tarjeta = Tarjeta.query.filter_by(estado="activa").first()
        tarjeta_id = tarjeta.id_tarjeta
        uid = tarjeta.uid
        trabajador_id = tarjeta.id_trabajador
        fecha = tarjeta.fecha_asignacion.strftime("%Y-%m-%d")

    _login(client)
    respuesta = client.post(
        f"/admin/tarjetas/{tarjeta_id}/editar",
        data={
            "uid": uid,
            "estado": "bloqueada",
            "id_trabajador": trabajador_id,
            "fecha_asignacion": fecha,
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    with app.app_context():
        tarjeta = db.session.get(Tarjeta, tarjeta_id)
        assert tarjeta.estado == "bloqueada"
        assert Auditoria.query.filter_by(accion="ADMIN_EDITAR").count() >= 1


def test_admin_elimina_sede_sin_dependencias(app, client):
    _login(client)
    client.post(
        "/admin/sedes/nuevo",
        data={"nombre": "Sede Temporal", "direccion": "Av. Temporal 10", "activa": "1"},
        follow_redirects=True,
    )
    with app.app_context():
        sede_id = Sede.query.filter_by(nombre="Sede Temporal").one().id_sede

    confirmacion = client.get(f"/admin/sedes/{sede_id}/eliminar")
    assert confirmacion.status_code == 200
    assert b"Esta acci" in confirmacion.data

    respuesta = client.post(f"/admin/sedes/{sede_id}/eliminar", follow_redirects=True)
    assert respuesta.status_code == 200
    with app.app_context():
        assert db.session.get(Sede, sede_id) is None
        assert Auditoria.query.filter_by(accion="ADMIN_ELIMINAR").count() == 1


def test_admin_no_elimina_sede_con_dependencias(app, client):
    with app.app_context():
        sede = Sede.query.filter(Sede.areas.any()).first()
        sede_id = sede.id_sede

    _login(client)
    pagina = client.get(f"/admin/sedes/{sede_id}/eliminar")
    assert pagina.status_code == 200
    assert "tiene áreas" in pagina.get_data(as_text=True)

    client.post(f"/admin/sedes/{sede_id}/eliminar", follow_redirects=True)
    with app.app_context():
        assert db.session.get(Sede, sede_id) is not None


def test_admin_sincroniza_lector(client):
    with client.application.app_context():
        lector = Lector.query.first()
        lector_id = lector.id_lector
    _login(client)
    respuesta = client.post(f"/admin/lectores/{lector_id}/sincronizar", follow_redirects=True)
    assert respuesta.status_code == 200
    with client.application.app_context():
        assert Auditoria.query.filter_by(accion="LECTOR_SINCRONIZADO").count() == 1


def test_admin_crea_usuario_con_password(app, client):
    with app.app_context():
        trabajador = (
            Trabajador.query.outerjoin(Usuario, Usuario.id_trabajador == Trabajador.id_trabajador)
            .filter(Usuario.id_usuario.is_(None))
            .first()
        )
        trabajador_id = trabajador.id_trabajador

    _login(client)
    respuesta = client.post(
        "/admin/usuarios/nuevo",
        data={
            "correo": "nuevo.admin@utsm.edu.pe",
            "rol": "trabajador",
            "id_trabajador": trabajador_id,
            "activo": "1",
            "password": "ClaveSegura123",
        },
        follow_redirects=True,
    )
    assert respuesta.status_code == 200
    with app.app_context():
        usuario = Usuario.query.filter_by(correo="nuevo.admin@utsm.edu.pe").first()
        assert usuario is not None
        assert usuario.check_password("ClaveSegura123")


def test_usuario_no_admin_no_entra_al_panel(client):
    _login(client, "trabajador@utsm.edu.pe", "trabajador123")
    respuesta = client.get("/admin")
    assert respuesta.status_code == 403
