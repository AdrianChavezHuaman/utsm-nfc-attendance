"""Pruebas de integridad de los datos maestros."""

from datetime import date

from app.models import Area, Horario, Lector, Sede, Tarjeta, Trabajador, Usuario


def test_conteos_base(app):
    with app.app_context():
        assert Sede.query.count() == 2
        assert Area.query.count() == 12
        assert Trabajador.query.count() == 280
        assert Tarjeta.query.count() == 280
        assert Horario.query.count() == 280 * 5
        assert Lector.query.count() == 8
        assert Usuario.query.count() == 5


def test_distribucion_de_trabajadores(app):
    with app.app_context():
        assert Trabajador.query.filter_by(tipo="admin").count() == 120
        assert Trabajador.query.filter_by(tipo="docente_tc").count() == 80
        assert Trabajador.query.filter_by(tipo="docente_tp").count() == 80


def test_nombres_de_trabajadores_unicos(app):
    with app.app_context():
        nombres = [trabajador.nombres for trabajador in Trabajador.query.all()]
        assert len(nombres) == 280
        assert len(set(nombres)) == 280


def test_tarjeta_unica_por_trabajador(app):
    with app.app_context():
        trabajadores_con_tarjeta = {t.id_trabajador for t in Tarjeta.query.all()}
        assert len(trabajadores_con_tarjeta) == 280
        assert {t.id_trabajador for t in Trabajador.query.all()} == trabajadores_con_tarjeta
        assert len({t.uid for t in Tarjeta.query.all()}) == 280


def test_horarios_lunes_a_viernes_y_turnos_variados(app):
    with app.app_context():
        for trabajador in Trabajador.query.limit(15):
            dias = sorted(h.dia_semana for h in trabajador.horarios)
            assert dias == [0, 1, 2, 3, 4]

        turnos = {(horario.hora_entrada, horario.hora_salida) for horario in Horario.query.all()}
        assert len(turnos) >= 8


def test_tarjetas_emitidas_el_27_12_2026(app):
    with app.app_context():
        fechas = {tarjeta.fecha_asignacion for tarjeta in Tarjeta.query.all()}
        assert fechas == {date(2026, 12, 27)}


def test_cuentas_demo_con_roles_y_password(app):
    with app.app_context():
        esperados = {
            "admin@utsm.edu.pe": "admin",
            "jefe@utsm.edu.pe": "jefe",
            "analista@utsm.edu.pe": "analista",
            "coordinador@utsm.edu.pe": "coordinador",
            "trabajador@utsm.edu.pe": "trabajador",
        }
        for correo, rol in esperados.items():
            usuario = Usuario.query.filter_by(correo=correo).first()
            assert usuario is not None
            assert usuario.rol == rol
            assert usuario.activo is True
            assert usuario.password_hash != "admin123"

        admin = Usuario.query.filter_by(correo="admin@utsm.edu.pe").first()
        assert admin.check_password("admin123")
        assert not admin.check_password("clave-incorrecta")


def test_seed_es_idempotente(app):
    from seeds.seed_base import seed_base

    with app.app_context():
        resultado = seed_base()
        assert resultado == {"existente": True}
        assert Trabajador.query.count() == 280
