"""Pruebas puras de las reglas R-01 a R-10."""

from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

from app.kiosk import rules


def _marca(tipo: str, fecha_hora: datetime, id_sede: int = 1):
    return SimpleNamespace(tipo=tipo, fecha_hora=fecha_hora, id_sede=id_sede)


def test_r01_tarjeta_valida():
    tarjeta = SimpleNamespace(estado="activa", id_trabajador=7)
    resultado = rules.validar_tarjeta(tarjeta)
    assert resultado.ok is True
    assert resultado.codigo == "OK"


def test_r01_tarjeta_inexistente():
    resultado = rules.validar_tarjeta(None)
    assert resultado.ok is False
    assert resultado.codigo == "TARJETA_NO_ENCONTRADA"


def test_r08_tarjeta_bloqueada():
    tarjeta = SimpleNamespace(estado="bloqueada", id_trabajador=7)
    resultado = rules.validar_tarjeta(tarjeta)
    assert resultado.ok is False
    assert resultado.codigo == "TARJETA_BLOQUEADA"


def test_r01_tarjeta_sin_trabajador():
    tarjeta = SimpleNamespace(estado="activa", id_trabajador=None)
    resultado = rules.validar_tarjeta(tarjeta)
    assert resultado.ok is False
    assert resultado.codigo == "TARJETA_SIN_TRABAJADOR"


def test_r02_duplicado_dentro_de_dos_minutos():
    ahora = datetime(2026, 11, 23, 8, 5)
    ultima = _marca("ingreso", ahora - timedelta(seconds=90))
    assert rules.es_duplicado(ultima, "ingreso", ahora) is True


def test_r02_no_es_duplicado_a_los_dos_minutos_o_mas():
    ahora = datetime(2026, 11, 23, 8, 5)
    ultima = _marca("ingreso", ahora - timedelta(minutes=2))
    assert rules.es_duplicado(ultima, "ingreso", ahora) is False


def test_r02_no_es_duplicado_si_cambia_el_tipo():
    ahora = datetime(2026, 11, 23, 8, 5)
    ultima = _marca("ingreso", ahora - timedelta(seconds=30))
    assert rules.es_duplicado(ultima, "salida", ahora) is False


def test_r03_entrada_dentro_de_tolerancia():
    horario = SimpleNamespace(hora_entrada=time(8, 0))
    resultado = rules.evaluar_tolerancia(horario, datetime(2026, 11, 23, 8, 10))
    assert resultado.ok is True


def test_r03_entrada_tardia_genera_observacion():
    horario = SimpleNamespace(hora_entrada=time(8, 0))
    resultado = rules.evaluar_tolerancia(horario, datetime(2026, 11, 23, 8, 21))
    assert resultado.ok is False
    assert resultado.observada is True
    assert resultado.incidencia == "fuera_horario"
    assert resultado.minutos_tarde == 21


def test_r03_entrada_anticipada_es_valida():
    horario = SimpleNamespace(hora_entrada=time(8, 0))
    resultado = rules.evaluar_tolerancia(horario, datetime(2026, 11, 23, 7, 40))
    assert resultado.ok is True


def test_r03_sin_horario_genera_observacion():
    resultado = rules.evaluar_tolerancia(None, datetime(2026, 11, 23, 8, 5))
    assert resultado.ok is False
    assert resultado.incidencia == "fuera_horario"


def test_r04_salida_sin_entrada():
    assert rules.incidencia_por_secuencia(None, "salida") == "falta_entrada"
    salida = _marca("salida", datetime(2026, 11, 23, 17, 0))
    assert rules.incidencia_por_secuencia(salida, "salida") == "falta_entrada"


def test_r04_secuencia_normal_no_genera_incidencia():
    ingreso = _marca("ingreso", datetime(2026, 11, 23, 8, 0))
    assert rules.incidencia_por_secuencia(ingreso, "salida") is None


def test_r04_ingreso_sin_salida_previa():
    ingreso = _marca("ingreso", datetime(2026, 11, 23, 8, 0))
    assert rules.incidencia_por_secuencia(ingreso, "ingreso") == "falta_salida"


def test_r05_plazo_de_cinco_dias_habiles():
    lunes = date(2026, 11, 23)
    viernes = date(2026, 11, 27)
    siguiente_lunes = date(2026, 11, 30)
    assert rules.justificacion_en_plazo(lunes, viernes) is True
    assert rules.justificacion_en_plazo(lunes, siguiente_lunes) is True
    assert rules.justificacion_en_plazo(lunes, date(2026, 12, 1)) is False


def test_r05_no_acepta_fechas_anteriores():
    assert rules.justificacion_en_plazo(date(2026, 11, 27), date(2026, 11, 23)) is False


def test_r06_coordinador_solo_su_area():
    assert rules.coordinador_puede_aprobar(3, 3) is True
    assert rules.coordinador_puede_aprobar(3, 4) is False
    assert rules.coordinador_puede_aprobar(None, 3) is False


def test_r07_periodo_cerrado_o_bloqueado():
    assert rules.periodo_bloqueado("abierto") is False
    assert rules.periodo_bloqueado("cerrado") is True
    assert rules.periodo_bloqueado("bloqueado") is True


def test_r09_dos_sedes_en_menos_de_treinta_minutos():
    ahora = datetime(2026, 11, 23, 8, 15)
    otra_sede = _marca("ingreso", ahora - timedelta(minutes=10), id_sede=2)
    assert rules.es_doble_sede(otra_sede, 1, ahora) is True
    assert rules.es_doble_sede(otra_sede, 2, ahora) is False


def test_r09_fuera_de_la_ventana_de_treinta_minutos():
    ahora = datetime(2026, 11, 23, 8, 30)
    otra_sede = _marca("ingreso", ahora - timedelta(minutes=30), id_sede=2)
    assert rules.es_doble_sede(otra_sede, 1, ahora) is False


def test_r10_conserva_la_hora_real():
    registrada = datetime(2026, 11, 23, 8, 5, 12)
    sincronizada = datetime(2026, 11, 23, 12, 40, 0)
    assert rules.hora_real(registrada, sincronizada) == registrada


def test_r08_bloqueo_de_tarjeta():
    assert rules.bloquear_tarjeta("activa") == "bloqueada"
    assert rules.bloquear_tarjeta("bloqueada") == "bloqueada"
