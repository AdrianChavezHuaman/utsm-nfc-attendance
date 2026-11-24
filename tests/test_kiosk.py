"""Pruebas de integración del kiosco y de sus reglas aplicadas."""

from datetime import datetime, time

from app.extensions import db
from app.kiosk.service import registrar_marcacion
from app.models import Auditoria, Horario, Incidencia, Lector, Marca, Trabajador


def _trabajador_con_tarjeta():
    """Busca un administrativo con turno de 8:00 para las horas del test."""
    trabajador = (
        Trabajador.query.join(Horario)
        .filter(
            Trabajador.tipo == "admin",
            Horario.dia_semana == 0,
            Horario.hora_entrada == time(8, 0),
        )
        .order_by(Trabajador.id_trabajador)
        .first()
    )
    assert trabajador is not None and trabajador.tarjeta is not None
    return trabajador


def _lector(tipo: str, sede_distinta_de: int | None = None):
    consulta = Lector.query.filter_by(tipo=tipo, estado="activo")
    if sede_distinta_de is not None:
        consulta = consulta.filter(Lector.id_sede != sede_distinta_de)
    lector = consulta.order_by(Lector.id_lector).first()
    assert lector is not None
    return lector


def _marcar(app, tipo: str, ahora: datetime, lector=None):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        lector = lector or _lector("entrada" if tipo == "ingreso" else "salida")
        return registrar_marcacion(
            trabajador.tarjeta.uid,
            tipo,
            lector.id_lector,
            ahora=ahora,
        )


def test_kiosco_carga_sin_sesion(client):
    respuesta = client.get("/kiosk")
    assert respuesta.status_code == 200
    assert b"Registra tu asistencia" in respuesta.data
    assert b"Tarjetas de demostraci" in respuesta.data


def test_marcacion_valida_crea_marca_y_auditoria(app):
    resultado = _marcar(app, "ingreso", datetime(2026, 11, 23, 8, 5))
    assert resultado["ok"] is True
    assert resultado["estado"] == "valida"
    with app.app_context():
        assert Marca.query.count() == 1
        assert Incidencia.query.count() == 0
        assert Auditoria.query.filter_by(accion="MARCA_INGRESO").count() == 1


def test_duplicado_ignora_el_segundo_intento(app):
    _marcar(app, "ingreso", datetime(2026, 11, 23, 8, 5))
    resultado = _marcar(app, "ingreso", datetime(2026, 11, 23, 8, 6))
    assert resultado["ok"] is False
    assert resultado["estado"] == "duplicado"
    with app.app_context():
        assert Marca.query.count() == 1
        assert Auditoria.query.filter_by(accion="MARCA_DUPLICADA").count() == 1


def test_entrada_tardia_genera_incidencia(app):
    resultado = _marcar(app, "ingreso", datetime(2026, 11, 23, 8, 21))
    assert resultado["ok"] is True
    assert resultado["estado"] == "observada"
    assert resultado["incidencia"] == "fuera_horario"
    with app.app_context():
        assert Marca.query.filter_by(estado="observada").count() == 1
        assert Incidencia.query.filter_by(tipo="fuera_horario").count() == 1


def test_salida_sin_entrada_genera_falta_entrada(app):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        lector = _lector("salida")
        resultado = registrar_marcacion(
            trabajador.tarjeta.uid,
            "salida",
            lector.id_lector,
            ahora=datetime(2026, 11, 23, 17, 5),
        )
        assert resultado["estado"] == "observada"
        assert resultado["incidencia"] == "falta_entrada"
        assert Incidencia.query.filter_by(tipo="falta_entrada").count() == 1


def test_ingreso_tras_ingreso_abierto_genera_falta_salida(app):
    _marcar(app, "ingreso", datetime(2026, 11, 23, 8, 5))
    resultado = _marcar(app, "ingreso", datetime(2026, 11, 23, 8, 20))
    assert resultado["ok"] is True
    with app.app_context():
        assert Incidencia.query.filter_by(tipo="falta_salida").count() == 1
        assert Marca.query.count() == 2


def test_dos_sedes_en_menos_de_treinta_minutos(app):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        entrada = _lector("entrada")
        salida_otra_sede = _lector("salida", sede_distinta_de=entrada.id_sede)

        registrar_marcacion(
            trabajador.tarjeta.uid,
            "ingreso",
            entrada.id_lector,
            ahora=datetime(2026, 11, 23, 8, 5),
        )
        resultado = registrar_marcacion(
            trabajador.tarjeta.uid,
            "salida",
            salida_otra_sede.id_lector,
            ahora=datetime(2026, 11, 23, 8, 15),
        )

        assert resultado["estado"] == "observada"
        assert resultado["incidencia"] == "doble_sede"
        assert Incidencia.query.filter_by(tipo="doble_sede").count() == 1


def test_tarjeta_bloqueada_no_registra_marca(app):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        trabajador.tarjeta.estado = "bloqueada"
        db.session.commit()
        lector = _lector("entrada")
        resultado = registrar_marcacion(
            trabajador.tarjeta.uid,
            "ingreso",
            lector.id_lector,
            ahora=datetime(2026, 11, 23, 8, 5),
        )
        assert resultado["ok"] is False
        assert resultado["estado"] == "error"
        assert Marca.query.count() == 0
        assert Auditoria.query.filter_by(accion="MARCA_RECHAZADA").count() == 1


def test_lector_incompatible_no_registra_marca(app):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        lector_salida = _lector("salida")
        resultado = registrar_marcacion(
            trabajador.tarjeta.uid,
            "ingreso",
            lector_salida.id_lector,
            ahora=datetime(2026, 11, 23, 8, 5),
        )
        assert resultado["ok"] is False
        assert resultado["estado"] == "error"
        assert Marca.query.count() == 0


def test_uid_desconocido(app):
    with app.app_context():
        lector = _lector("entrada")
        resultado = registrar_marcacion(
            "UTSM-9999",
            "ingreso",
            lector.id_lector,
            ahora=datetime(2026, 11, 23, 8, 5),
        )
        assert resultado["ok"] is False
        assert resultado["estado"] == "error"
        assert Marca.query.count() == 0


def test_api_marca_responde_json(app, client):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        uid = trabajador.tarjeta.uid
        lector = _lector("entrada")

    respuesta = client.post(
        "/api/marca",
        json={"uid": uid, "tipo": "ingreso", "id_lector": lector.id_lector},
    )
    assert respuesta.status_code == 200
    datos = respuesta.get_json()
    assert datos["ok"] is True
    assert datos["estado"] in ("valida", "observada")
    assert datos["trabajador"]
    with app.app_context():
        assert Marca.query.count() == 1


def test_post_de_respaldo_del_kiosco(app, client):
    with app.app_context():
        trabajador = _trabajador_con_tarjeta()
        uid = trabajador.tarjeta.uid
        lector = _lector("entrada")

    respuesta = client.post(
        "/kiosk",
        data={"uid": uid, "tipo": "ingreso", "id_lector": lector.id_lector},
    )
    assert respuesta.status_code == 200
    assert b"result--" in respuesta.data
    with app.app_context():
        assert Marca.query.count() == 1
