"""Registro declarativo de entidades del panel de administración."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, time
from typing import Any

from ..models import Area, Horario, Lector, Sede, Tarjeta, Trabajador, Usuario

DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
TIPOS_TRABAJADOR = (
    ("admin", "Administrativo"),
    ("docente_tc", "Docente TC"),
    ("docente_tp", "Docente TP"),
)
ROLES = (
    ("trabajador", "Trabajador"),
    ("coordinador", "Coordinador de área"),
    ("analista", "Analista de RR. HH."),
    ("jefe", "Jefe de RR. HH."),
    ("admin", "Administrador"),
)
ESTADOS_TARJETA = (("activa", "Activa"), ("bloqueada", "Bloqueada"), ("repuesta", "Repuesta"))
ESTADOS_LECTOR = (
    ("activo", "Activo"),
    ("inactivo", "Inactivo"),
    ("mantenimiento", "Mantenimiento"),
)
TIPOS_LECTOR = (("entrada", "Entrada"), ("salida", "Salida"))
TIPOS_TURNO = (("completo", "Completo"), ("parcial", "Parcial"), ("nocturno", "Nocturno"))


@dataclass(frozen=True)
class Campo:
    nombre: str
    etiqueta: str
    tipo: str = "text"
    requerido: bool = True
    opciones: Callable[[], list[tuple[str, str]]] | list[tuple[str, str]] | None = None
    default: Any = ""
    ayuda: str = ""
    ancho: str = "half"


@dataclass(frozen=True)
class Entidad:
    slug: str
    nombre: str
    singular: str
    descripcion: str
    modelo: type
    pk: str
    campos: tuple[Campo, ...]
    columnas: tuple[tuple[str, Callable], ...]
    buscar: tuple[str, ...]
    orden: str
    icono: str = "users"
    etiqueta_nueva: str = "Nuevo registro"


def _opciones_sedes() -> list[tuple[str, str]]:
    return [(str(sede.id_sede), sede.nombre) for sede in Sede.query.order_by(Sede.nombre)]


def _opciones_areas() -> list[tuple[str, str]]:
    return [
        (str(area.id_area), f"{area.nombre} · {area.sede.nombre}")
        for area in Area.query.order_by(Area.nombre)
    ]


def _opciones_trabajadores() -> list[tuple[str, str]]:
    return [
        (
            str(trabajador.id_trabajador),
            f"{trabajador.dni} · {trabajador.nombre_corto} · {trabajador.area.nombre}",
        )
        for trabajador in Trabajador.query.order_by(Trabajador.nombres)
    ]


def _tipo_trabajador(valor: str) -> str:
    return dict(TIPOS_TRABAJADOR).get(valor, valor)


def _sede_de(objeto) -> str:
    return objeto.sede.nombre if objeto.sede else "—"


ENTIDADES: tuple[Entidad, ...] = (
    Entidad(
        slug="sedes",
        nombre="Sedes",
        singular="Sede",
        descripcion="Sedes físicas donde se instalan lectores y trabajadores.",
        modelo=Sede,
        pk="id_sede",
        campos=(
            Campo("nombre", "Nombre", requerido=True),
            Campo("direccion", "Dirección", requerido=False, ancho="full"),
            Campo("activa", "Sede activa", tipo="checkbox", default=True),
        ),
        columnas=(
            ("Sede", lambda o: o.nombre),
            ("Dirección", lambda o: o.direccion or "—"),
            ("Activa", lambda o: "Sí" if o.activa else "No"),
        ),
        buscar=("nombre", "direccion"),
        orden="nombre",
        icono="building",
    ),
    Entidad(
        slug="areas",
        nombre="Áreas",
        singular="Área",
        descripcion="Áreas y escuelas a las que pertenece el personal.",
        modelo=Area,
        pk="id_area",
        campos=(
            Campo("nombre", "Nombre", requerido=True),
            Campo("id_sede", "Sede", tipo="select_int", opciones=_opciones_sedes),
        ),
        columnas=(
            ("Área", lambda o: o.nombre),
            ("Sede", _sede_de),
            ("Trabajadores", lambda o: len(o.trabajadores)),
        ),
        buscar=("nombre",),
        orden="nombre",
        icono="layers",
    ),
    Entidad(
        slug="trabajadores",
        nombre="Trabajadores",
        singular="Trabajador",
        descripcion="Personal docente y administrativo incluido en la planilla.",
        modelo=Trabajador,
        pk="id_trabajador",
        campos=(
            Campo("dni", "DNI", requerido=True),
            Campo("nombres", "Nombres completos", requerido=True),
            Campo("cargo", "Cargo", requerido=True),
            Campo("tipo", "Tipo de personal", tipo="select", opciones=TIPOS_TRABAJADOR),
            Campo("id_area", "Área", tipo="select_int", opciones=_opciones_areas),
            Campo("activo", "Trabajador activo", tipo="checkbox", default=True),
        ),
        columnas=(
            ("DNI", lambda o: o.dni),
            ("Trabajador", lambda o: o.nombre_corto),
            ("Cargo", lambda o: o.cargo),
            ("Tipo", lambda o: _tipo_trabajador(o.tipo)),
            ("Área", lambda o: o.area.nombre),
            ("Activo", lambda o: "Sí" if o.activo else "No"),
        ),
        buscar=("dni", "nombres", "cargo"),
        orden="nombres",
        icono="users",
    ),
    Entidad(
        slug="tarjetas",
        nombre="Tarjetas NFC",
        singular="Tarjeta",
        descripcion="Tarjetas asignadas a un único trabajador. Una tarjeta perdida se bloquea.",
        modelo=Tarjeta,
        pk="id_tarjeta",
        campos=(
            Campo("uid", "UID de tarjeta", requerido=True),
            Campo("estado", "Estado", tipo="select", opciones=ESTADOS_TARJETA, default="activa"),
            Campo(
                "id_trabajador", "Trabajador", tipo="select_int", opciones=_opciones_trabajadores
            ),
            Campo("fecha_asignacion", "Fecha de asignación", tipo="date", default=date.today()),
        ),
        columnas=(
            ("UID", lambda o: o.uid),
            ("Trabajador", lambda o: o.trabajador.nombre_corto),
            ("Estado", lambda o: o.estado.capitalize()),
            ("Asignada", lambda o: o.fecha_asignacion.strftime("%d/%m/%Y")),
        ),
        buscar=("uid",),
        orden="uid",
        icono="card",
    ),
    Entidad(
        slug="horarios",
        nombre="Horarios",
        singular="Horario",
        descripcion="Patrón semanal por trabajador, con turnos y días laborables.",
        modelo=Horario,
        pk="id_horario",
        campos=(
            Campo(
                "id_trabajador", "Trabajador", tipo="select_int", opciones=_opciones_trabajadores
            ),
            Campo(
                "dia_semana",
                "Día",
                tipo="select_int",
                opciones=[(str(i), d) for i, d in enumerate(DIAS)],
            ),
            Campo("hora_entrada", "Hora de entrada", tipo="time", default=time(8, 0)),
            Campo("hora_salida", "Hora de salida", tipo="time", default=time(17, 0)),
            Campo("tipo_turno", "Turno", tipo="select", opciones=TIPOS_TURNO, default="completo"),
        ),
        columnas=(
            ("Trabajador", lambda o: o.trabajador.nombre_corto),
            ("Día", lambda o: DIAS[o.dia_semana]),
            ("Entrada", lambda o: o.hora_entrada.strftime("%H:%M")),
            ("Salida", lambda o: o.hora_salida.strftime("%H:%M")),
            ("Turno", lambda o: o.tipo_turno.capitalize()),
        ),
        buscar=(),
        orden="id_trabajador",
        icono="clock",
    ),
    Entidad(
        slug="lectores",
        nombre="Lectores NFC",
        singular="Lector",
        descripcion="Lectores instalados por sede, con sincronización online/offline.",
        modelo=Lector,
        pk="id_lector",
        campos=(
            Campo("nombre", "Nombre", requerido=True),
            Campo("id_sede", "Sede", tipo="select_int", opciones=_opciones_sedes),
            Campo("tipo", "Tipo", tipo="select", opciones=TIPOS_LECTOR),
            Campo("estado", "Estado", tipo="select", opciones=ESTADOS_LECTOR, default="activo"),
        ),
        columnas=(
            ("Lector", lambda o: o.nombre),
            ("Sede", _sede_de),
            ("Tipo", lambda o: o.tipo.capitalize()),
            ("Estado", lambda o: o.estado.capitalize()),
        ),
        buscar=("nombre",),
        orden="nombre",
        icono="scan",
    ),
    Entidad(
        slug="usuarios",
        nombre="Usuarios",
        singular="Usuario",
        descripcion="Cuentas de acceso con rol y vínculo al trabajador.",
        modelo=Usuario,
        pk="id_usuario",
        campos=(
            Campo("correo", "Correo institucional", requerido=True),
            Campo("rol", "Rol", tipo="select", opciones=ROLES, default="trabajador"),
            Campo(
                "id_trabajador",
                "Trabajador vinculado",
                tipo="select_int",
                requerido=False,
                opciones=_opciones_trabajadores,
            ),
            Campo("activo", "Cuenta activa", tipo="checkbox", default=True),
            Campo(
                "password",
                "Contraseña",
                tipo="password",
                requerido=False,
                ayuda="Obligatoria al crear; mínimo 8 caracteres con letra y número. Déjala vacía para conservarla.",
                ancho="full",
            ),
        ),
        columnas=(
            ("Correo", lambda o: o.correo),
            ("Rol", lambda o: dict(ROLES).get(o.rol, o.rol)),
            ("Trabajador", lambda o: o.trabajador.nombre_corto if o.trabajador else "—"),
            ("Activo", lambda o: "Sí" if o.activo else "No"),
        ),
        buscar=("correo", "rol"),
        orden="correo",
        icono="shield",
    ),
)

ENTIDADES_POR_SLUG = {entidad.slug: entidad for entidad in ENTIDADES}
