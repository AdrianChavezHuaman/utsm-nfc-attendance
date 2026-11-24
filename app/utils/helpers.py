"""Helpers de presentación y validación."""

from datetime import datetime
from urllib.parse import urlparse

ROLES = {
    "trabajador": "Trabajador",
    "coordinador": "Coordinador de área",
    "analista": "Analista de RR. HH.",
    "jefe": "Jefe de RR. HH.",
    "admin": "Administrador",
}

# Roles con acentos de la misma familia: verde, latón, arcilla y teal.
ROLE_COLORS = {
    "trabajador": "sage",
    "coordinador": "brass",
    "analista": "teal",
    "jefe": "clay",
    "admin": "forest",
}

ACCIONES = {
    "LOGIN": "Inicio de sesión",
    "LOGOUT": "Cierre de sesión",
    "LOGIN_FALLIDO": "Intento fallido",
    "LOGIN_BLOQUEADO": "Cuenta bloqueada",
    "MARCA_INGRESO": "Ingreso registrado",
    "MARCA_SALIDA": "Salida registrada",
    "MARCA_DUPLICADA": "Duplicado ignorado",
    "MARCA_RECHAZADA": "Marcación rechazada",
    "JUSTIFICACION_ENVIADA": "Justificación enviada",
    "JUSTIFICACION_APROBADA": "Justificación aprobada",
    "JUSTIFICACION_RECHAZADA": "Justificación rechazada",
    "PERIODO_CERRADO": "Periodo cerrado",
    "EXCEPCION_CORREGIDA": "Excepción corregida",
    "CORREGIR_MARCA": "Marcación corregida",
    "EXPORTACION": "Exportación generada",
    "ADMIN_CREAR": "Registro creado",
    "ADMIN_EDITAR": "Registro editado",
    "ADMIN_ELIMINAR": "Registro eliminado",
    "LECTOR_SINCRONIZADO": "Lector sincronizado",
    "HORARIO_ACTUALIZADO": "Horario semanal actualizado",
    "SEED_HISTORICO": "Línea base histórica",
}

ESTADOS_PERIODO_LABEL = {
    "abierto": "Abierto",
    "cerrado": "Cerrado",
    "bloqueado": "Bloqueado",
}

TIPOS_INCIDENCIA_LABEL = {
    "falta_entrada": "Salida sin entrada",
    "falta_salida": "Entrada sin salida",
    "fuera_horario": "Fuera de horario",
    "duplicado": "Duplicado",
    "doble_sede": "Doble sede",
}

TIPOS_MARCA_LABEL = {"ingreso": "Ingreso", "salida": "Salida"}

ESTADOS_JUSTIFICACION_LABEL = {
    "enviada": "En revisión",
    "aprobada": "Aprobada",
    "rechazada": "Rechazada",
}

DIAS = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")
MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def role_label(rol: str | None) -> str:
    """Devuelve la etiqueta legible de un rol."""
    return ROLES.get(rol or "", "Sin rol")


def role_color(rol: str | None) -> str:
    return ROLE_COLORS.get(rol or "", "forest")


def initials(nombre: str | None) -> str:
    """Iniciales para el avatar (máximo dos letras)."""
    if not nombre:
        return "US"
    partes = [p for p in nombre.replace(".", " ").split() if p]
    if not partes:
        return "US"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[1][0]).upper()


def fecha_legible(valor: datetime | None = None) -> str:
    """Fecha corta en español: 'lun 23 nov 2026'."""
    valor = valor or datetime.now()
    return f"{DIAS[valor.weekday()]} {valor.day:02d} {MESES[valor.month - 1]} {valor.year}"


def accion_label(accion: str) -> str:
    """Traduce las acciones de auditoría a lenguaje de interfaz."""
    return ACCIONES.get(accion, accion.replace("_", " ").capitalize())


def tipo_incidencia_label(tipo: str | None) -> str:
    return TIPOS_INCIDENCIA_LABEL.get(
        tipo or "", (tipo or "Sin tipo").replace("_", " ").capitalize()
    )


def tipo_marca_label(tipo: str | None) -> str:
    return TIPOS_MARCA_LABEL.get(tipo or "", tipo or "—")


def estado_justificacion_label(estado: str | None) -> str:
    return ESTADOS_JUSTIFICACION_LABEL.get(estado or "", estado or "—")


def estado_periodo(estado: str | None) -> dict[str, str]:
    """Etiqueta y color de badge para el estado de un periodo."""
    estado = estado or "abierto"
    badge = {"abierto": "brass", "cerrado": "jade", "bloqueado": "muted"}.get(estado, "muted")
    return {"label": ESTADOS_PERIODO_LABEL.get(estado, estado.capitalize()), "badge": badge}


def estado_incidencia(incidencia) -> dict[str, str]:
    """Etiqueta y color de badge para el estado visible de una incidencia."""
    if incidencia.estado == "justificada":
        return {"label": "Justificada", "badge": "jade"}
    if incidencia.estado == "rechazada":
        return {"label": "Rechazada", "badge": "clay"}
    if incidencia.estado == "cerrada":
        return {"label": "Cerrada", "badge": "muted"}

    justificacion = getattr(incidencia, "justificacion", None)
    if justificacion is not None and justificacion.estado == "enviada":
        return {"label": "En revisión", "badge": "brass"}
    return {"label": "Pendiente", "badge": "brass"}


def is_safe_url(target: str | None) -> bool:
    """Evita redirecciones abiertas: solo rutas relativas del mismo host."""
    if not target:
        return False
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return False
    return target.startswith("/") and not target.startswith("//")


def miles(valor, decimales: int = 0) -> str:
    """Formatea un número con separador de miles."""
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    if decimales:
        return f"{numero:,.{decimales}f}"
    return f"{round(numero):,}"
