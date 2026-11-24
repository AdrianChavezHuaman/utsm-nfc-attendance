"""Reglas de negocio puras R-01 a R-10 del proceso AP-GTH-01.

No tocan la base de datos: reciben objetos o valores y devuelven resultados
verificables. El servicio del kiosco las compone; las pruebas las aíslan.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta

VENTANA_DUPLICADO = timedelta(minutes=2)
TOLERANCIA_ENTRADA_MIN = 10
VENTANA_DOS_SEDES = timedelta(minutes=30)
PLAZO_JUSTIFICACION_DIAS = 5


@dataclass(frozen=True)
class Validacion:
    """Resultado de una regla que puede generar una observación."""

    ok: bool
    codigo: str
    mensaje: str
    incidencia: str | None = None
    observada: bool = False
    minutos_tarde: int = 0
    alerta: bool = False


def validar_tarjeta(tarjeta) -> Validacion:
    """R-01 / R-08: tarjeta existente, activa y asignada a un trabajador."""
    if tarjeta is None:
        return Validacion(False, "TARJETA_NO_ENCONTRADA", "La tarjeta no está registrada.")
    if tarjeta.estado == "bloqueada":
        return Validacion(False, "TARJETA_BLOQUEADA", "La tarjeta está bloqueada.")
    if tarjeta.estado != "activa":
        return Validacion(
            False,
            "TARJETA_INACTIVA",
            f"La tarjeta está en estado '{tarjeta.estado}'.",
        )
    if not tarjeta.id_trabajador:
        return Validacion(
            False,
            "TARJETA_SIN_TRABAJADOR",
            "La tarjeta no tiene un trabajador asignado.",
        )
    return Validacion(True, "OK", "Tarjeta válida.")


def es_duplicado(ultima_marca, tipo: str, ahora: datetime) -> bool:
    """R-02: misma marcación dentro de la ventana de dos minutos."""
    if ultima_marca is None or ultima_marca.tipo != tipo:
        return False
    transcurrido = ahora - ultima_marca.fecha_hora
    return timedelta(0) <= transcurrido < VENTANA_DUPLICADO


def evaluar_tolerancia(horario, ahora: datetime) -> Validacion:
    """R-03: tolerancia de entrada de diez minutos; después, observada."""
    if horario is None:
        return Validacion(
            False,
            "SIN_HORARIO",
            "No hay un horario programado para hoy.",
            incidencia="fuera_horario",
            observada=True,
        )

    hora_esperada = datetime.combine(ahora.date(), horario.hora_entrada)
    limite = hora_esperada + timedelta(minutes=TOLERANCIA_ENTRADA_MIN)
    if ahora <= limite:
        return Validacion(True, "EN_TIEMPO", "Entrada dentro de la tolerancia.")

    minutos = int((ahora - hora_esperada).total_seconds() // 60)
    return Validacion(
        False,
        "TARDANZA",
        f"Entrada tardía: {minutos} min después de la hora programada.",
        incidencia="fuera_horario",
        observada=True,
        minutos_tarde=minutos,
    )


def incidencia_por_secuencia(ultima_marca, tipo: str) -> str | None:
    """R-04: salida sin entrada o entrada previa sin salida."""
    if tipo == "salida" and (ultima_marca is None or ultima_marca.tipo != "ingreso"):
        return "falta_entrada"
    if tipo == "ingreso" and ultima_marca is not None and ultima_marca.tipo == "ingreso":
        return "falta_salida"
    return None


def es_doble_sede(ultima_marca, id_sede_actual: int, ahora: datetime) -> bool:
    """R-09: dos sedes distintas en menos de treinta minutos."""
    if ultima_marca is None or ultima_marca.id_sede == id_sede_actual:
        return False
    transcurrido = ahora - ultima_marca.fecha_hora
    return timedelta(0) <= transcurrido < VENTANA_DOS_SEDES


def hora_real(fecha_registrada: datetime, fecha_sincronizacion: datetime | None = None) -> datetime:
    """R-10: conserva la hora real del evento aunque se sincronice después."""
    return fecha_registrada


def dias_habiles_entre(desde: date, hasta: date) -> int:
    """Días hábiles transcurridos (lunes a viernes, sin feriados)."""
    if hasta < desde:
        return -1
    dias = 0
    cursor = desde
    while cursor < hasta:
        cursor += timedelta(days=1)
        if cursor.weekday() < 5:
            dias += 1
    return dias


def justificacion_en_plazo(
    fecha_incidencia: date,
    hoy: date,
    plazo: int = PLAZO_JUSTIFICACION_DIAS,
) -> bool:
    """R-05: la justificación se presenta dentro de cinco días hábiles."""
    transcurridos = dias_habiles_entre(fecha_incidencia, hoy)
    return 0 <= transcurridos <= plazo


def coordinador_puede_aprobar(
    id_area_coordinador: int | None,
    id_area_incidencia: int | None,
) -> bool:
    """R-06: el coordinador solo aprueba incidencias de su área."""
    return (
        id_area_coordinador is not None
        and id_area_incidencia is not None
        and id_area_coordinador == id_area_incidencia
    )


def periodo_bloqueado(estado: str | None) -> bool:
    """R-07: un periodo cerrado o bloqueado no se edita sin auditoría."""
    return estado in {"cerrado", "bloqueado"}


def bloquear_tarjeta(estado_actual: str | None = None) -> str:
    """R-08: una tarjeta perdida pasa a bloqueada de inmediato."""
    return "bloqueada"
