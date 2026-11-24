"""Pruebas del flujo de incidencias, justificaciones y aprobaciones."""

from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path

from app.extensions import db
from app.kiosk.service import registrar_marcacion
from app.models import (
    Area,
    Auditoria,
    Incidencia,
    Justificacion,
    Lector,
    Marca,
    Trabajador,
    Usuario,
)

MOTIVO = "El lector no registró mi salida por una incidencia técnica del equipo."


def _archivo():
    return (BytesIO(b"%PDF-1.4\n% justificacion de prueba\n"), "sustento.pdf")


CREDENCIALES = {
    "trabajador": ("trabajador@utsm.edu.pe", "trabajador123"),
    "coordinador": ("coordinador@utsm.edu.pe", "coordinador123"),
    "analista": ("analista@utsm.edu.pe", "analista123"),
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


def _usuario(app, rol: str) -> Usuario:
    correo, _ = CREDENCIALES[rol]
    return Usuario.query.filter_by(correo=correo).first()


def _lector(tipo: str = "salida") -> Lector:
    return Lector.query.filter_by(tipo=tipo, estado="activo").order_by(Lector.id_lector).first()


def _crear_incidencia(app, correo: str = "trabajador@utsm.edu.pe", ahora=None) -> int:
    with app.app_context():
        usuario = Usuario.query.filter_by(correo=correo).first()
        trabajador = usuario.trabajador
        lector = _lector("salida")
        registrar_marcacion(
            trabajador.tarjeta.uid,
            "salida",
            lector.id_lector,
            ahora=ahora or datetime.now(),
        )
        incidencia = Incidencia.query.order_by(Incidencia.id_incidencia.desc()).first()
        return incidencia.id_incidencia


def _crear_incidencia_otra_area(app) -> tuple[int, str]:
    with app.app_context():
        trabajador = (
            Trabajador.query.join(Area)
            .filter(Area.nombre == "Escuela de Ingeniería de Sistemas")
            .order_by(Trabajador.id_trabajador)
            .first()
        )
        lector = _lector("salida")
        registrar_marcacion(
            trabajador.tarjeta.uid,
            "salida",
            lector.id_lector,
            ahora=datetime.now(),
        )
        incidencia = Incidencia.query.order_by(Incidencia.id_incidencia.desc()).first()
        return incidencia.id_incidencia, trabajador.nombres


def _justificar(client, incidencia_id: int):
    return client.post(
        f"/incidencias/{incidencia_id}/justificar",
        data={"motivo": MOTIVO, "archivo": _archivo()},
        content_type="multipart/form-data",
        follow_redirects=True,
    )


def _crear_justificacion_directa(app, incidencia_id: int) -> int:
    with app.app_context():
        incidencia = db.session.get(Incidencia, incidencia_id)
        justificacion = Justificacion(
            motivo=MOTIVO,
            estado="enviada",
            fecha_envio=datetime.now(),
            incidencia=incidencia,
        )
        db.session.add(justificacion)
        db.session.commit()
        return justificacion.id_justificacion


def test_trabajador_ve_solo_sus_incidencias(app, client):
    incidencia_id = _crear_incidencia(app)
    _login(client, "trabajador")
    respuesta = client.get("/mis-incidencias")
    assert respuesta.status_code == 200
    assert b"Mis incidencias" in respuesta.data
    assert b"Salida sin entrada" in respuesta.data
    assert f"/incidencias/{incidencia_id}".encode() in respuesta.data


def test_trabajador_justifica_y_adjunta_archivo(app, client):
    incidencia_id = _crear_incidencia(app)
    _login(client, "trabajador")

    respuesta = _justificar(client, incidencia_id)
    assert respuesta.status_code == 200
    assert b"Justificaci" in respuesta.data

    with app.app_context():
        justificacion = Justificacion.query.filter_by(id_incidencia=incidencia_id).first()
        assert justificacion is not None
        assert justificacion.estado == "enviada"
        assert justificacion.archivo_original == "sustento.pdf"
        assert justificacion.archivo
        ruta = Path(app.config["UPLOAD_FOLDER"]) / justificacion.archivo
        assert ruta.exists()
        assert ruta.read_bytes().startswith(b"%PDF")
        assert justificacion.incidencia.estado == "pendiente"
        assert Auditoria.query.filter_by(accion="JUSTIFICACION_ENVIADA").count() == 1


def test_coordinador_aprueba_justificacion_de_su_area(app, client):
    incidencia_id = _crear_incidencia(app)
    _login(client, "trabajador")
    _justificar(client, incidencia_id)
    _logout(client)

    _login(client, "coordinador")
    bandeja = client.get("/bandeja-coordinador")
    assert bandeja.status_code == 200
    assert b"Bandeja de mi" in bandeja.data

    respuesta = client.post(
        f"/incidencias/{incidencia_id}/resolver",
        data={"comentario": "Sustento válido.", "aprobar": "1"},
        follow_redirects=True,
    )
    assert respuesta.status_code == 200

    with app.app_context():
        justificacion = Justificacion.query.filter_by(id_incidencia=incidencia_id).first()
        incidencia = db.session.get(Incidencia, incidencia_id)
        assert justificacion.estado == "aprobada"
        assert incidencia.estado == "justificada"
        assert Auditoria.query.filter_by(accion="JUSTIFICACION_APROBADA").count() == 1


def test_rechazo_exige_comentario_y_permite_reenvio(app, client):
    incidencia_id = _crear_incidencia(app)
    _login(client, "trabajador")
    _justificar(client, incidencia_id)
    _logout(client)

    _login(client, "coordinador")
    sin_comentario = client.post(
        f"/incidencias/{incidencia_id}/resolver",
        data={"rechazar": "1"},
        follow_redirects=True,
    )
    assert b"motivo del rechazo" in sin_comentario.data

    with app.app_context():
        justificacion = Justificacion.query.filter_by(id_incidencia=incidencia_id).first()
        assert justificacion.estado == "enviada"

    client.post(
        f"/incidencias/{incidencia_id}/resolver",
        data={"rechazar": "1", "comentario": "El archivo no es legible."},
        follow_redirects=True,
    )
    with app.app_context():
        justificacion = Justificacion.query.filter_by(id_incidencia=incidencia_id).first()
        assert justificacion.estado == "rechazada"
        assert justificacion.incidencia.estado == "rechazada"

    _logout(client)
    _login(client, "trabajador")
    reenvio = _justificar(client, incidencia_id)
    assert reenvio.status_code == 200
    with app.app_context():
        justificacion = Justificacion.query.filter_by(id_incidencia=incidencia_id).first()
        assert justificacion.estado == "enviada"
        assert justificacion.incidencia.estado == "pendiente"


def test_coordinador_no_ve_ni_resuelve_otra_area(app, client):
    incidencia_id, nombre = _crear_incidencia_otra_area(app)
    _crear_justificacion_directa(app, incidencia_id)
    _login(client, "coordinador")

    bandeja = client.get("/bandeja-coordinador")
    assert bandeja.status_code == 200
    assert nombre.encode() not in bandeja.data

    respuesta = client.post(
        f"/incidencias/{incidencia_id}/resolver",
        data={"aprobar": "1"},
    )
    assert respuesta.status_code == 403


def test_trabajador_no_ve_incidencia_de_otro(app, client):
    incidencia_id, _nombre = _crear_incidencia_otra_area(app)
    _login(client, "trabajador")
    respuesta = client.get(f"/incidencias/{incidencia_id}")
    assert respuesta.status_code == 403


def test_analista_puede_consultar_todas_las_incidencias(app, client):
    _crear_incidencia_otra_area(app)
    _login(client, "analista")
    respuesta = client.get("/incidencias")
    assert respuesta.status_code == 200
    assert b"Incidencias del proceso" in respuesta.data
    assert b"Vista de an" in respuesta.data


def test_justificacion_fuera_de_plazo_se_bloquea(app, client):
    with app.app_context():
        usuario = _usuario(app, "trabajador")
        trabajador = usuario.trabajador
        lector = _lector("salida")
        marca = Marca(
            fecha_hora=datetime.now() - timedelta(days=10),
            tipo="salida",
            estado="observada",
            medio="nfc",
            id_trabajador=trabajador.id_trabajador,
            id_lector=lector.id_lector,
            id_sede=lector.id_sede,
        )
        db.session.add(marca)
        db.session.flush()
        incidencia = Incidencia(
            tipo="falta_entrada",
            estado="pendiente",
            observacion="Fuera de plazo para la prueba.",
            id_marca=marca.id_marca,
            id_trabajador=trabajador.id_trabajador,
        )
        db.session.add(incidencia)
        db.session.commit()
        incidencia_id = incidencia.id_incidencia

    _login(client, "trabajador")
    respuesta = client.get(
        f"/incidencias/{incidencia_id}/justificar",
        follow_redirects=True,
    )
    assert b"plazo de cinco" in respuesta.data.lower()

    respuesta = _justificar(client, incidencia_id)
    assert respuesta.status_code == 200
    with app.app_context():
        assert Justificacion.query.filter_by(id_incidencia=incidencia_id).count() == 0


def test_descarga_de_sustento_protegida(app, client):
    incidencia_id = _crear_incidencia(app)
    _login(client, "trabajador")
    _justificar(client, incidencia_id)

    archivo = client.get(f"/incidencias/{incidencia_id}/sustento")
    assert archivo.status_code == 200
    assert archivo.data.startswith(b"%PDF")

    _logout(client)
    anonimo = client.get(f"/incidencias/{incidencia_id}/sustento")
    assert anonimo.status_code == 302


def test_resumen_de_justificaciones_por_rol(app):
    _crear_incidencia(app)
    with app.app_context():
        from app.incidents.service import resumen_justificaciones

        trabajador = _usuario(app, "trabajador")
        coordinador = _usuario(app, "coordinador")
        analista = _usuario(app, "analista")
        assert resumen_justificaciones(trabajador)["sin_justificar"] == 1
        assert resumen_justificaciones(coordinador)["sin_justificar"] == 1
        assert resumen_justificaciones(analista)["sin_justificar"] == 1
