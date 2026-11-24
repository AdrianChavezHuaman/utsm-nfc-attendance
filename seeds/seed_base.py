"""Datos maestros ficticios de la UTSM.

Crea 2 sedes, 12 áreas, 280 trabajadores (120 administrativos, 80 docentes TC
y 80 docentes TP), una tarjeta NFC por trabajador, horarios de lunes a viernes,
8 lectores y las 5 cuentas de demostración (una por rol).

Uso directo:
    .venv/bin/python seeds/seed_base.py

También disponible como comando Flask:
    .venv/bin/flask --app run.py seed-base
"""

import random
import sys
from datetime import date, time, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.extensions import db  # noqa: E402
from app.models import (  # noqa: E402
    Area,
    Horario,
    Lector,
    Sede,
    Tarjeta,
    Trabajador,
    Usuario,
)

random.seed(20261123)
HOY = date.today()

# ---------------------------------------------------------------------------
# Catálogos ficticios
# ---------------------------------------------------------------------------
SEDES = [
    ("Sede Lima Norte", "Av. Universitaria 1234, Los Olivos, Lima"),
    ("Sede Lima Sur", "Av. El Sol 456, Villa El Salvador, Lima"),
]

# (nombre, índice de sede, tipo de área)
AREAS = [
    ("Rectorado", 0, "admin"),
    ("Recursos Humanos", 0, "admin"),
    ("Contabilidad y Finanzas", 0, "admin"),
    ("Dirección Académica", 0, "admin"),
    ("Biblioteca Central", 0, "admin"),
    ("Escuela de Ingeniería de Sistemas", 0, "docente"),
    ("Escuela de Administración", 0, "docente"),
    ("Escuela de Derecho", 1, "docente"),
    ("Escuela de Enfermería", 1, "docente"),
    ("Escuela de Educación", 1, "docente"),
    ("Logística y Servicios", 1, "admin"),
    ("Bienestar Universitario", 1, "admin"),
]

NOMBRES_MASCULINOS = [
    "Carlos",
    "Jorge",
    "Luis",
    "Miguel",
    "José",
    "Juan",
    "Diego",
    "Andrés",
    "Fernando",
    "Ricardo",
    "Marco",
    "Pedro",
    "Raúl",
    "Sergio",
    "Víctor",
    "Alonso",
    "Bruno",
    "Eduardo",
    "Gabriel",
    "Héctor",
]
NOMBRES_FEMENINOS = [
    "María",
    "Ana",
    "Lucía",
    "Carmen",
    "Rosa",
    "Patricia",
    "Sandra",
    "Claudia",
    "Verónica",
    "Silvia",
    "Daniela",
    "Gabriela",
    "Paola",
    "Milagros",
    "Elena",
    "Andrea",
    "Valeria",
    "Camila",
    "Fiorella",
    "Natalia",
]
APELLIDOS = [
    "Quispe",
    "Flores",
    "Salazar",
    "Rojas",
    "Huamán",
    "Vargas",
    "Castillo",
    "Ramírez",
    "Mendoza",
    "Torres",
    "García",
    "Ríos",
    "Chávez",
    "Paredes",
    "Sánchez",
    "Reyes",
    "Córdova",
    "Vega",
    "Palacios",
    "Espinoza",
    "Cruz",
    "Guzmán",
    "Campos",
    "Aguilar",
    "Bravo",
    "Carrasco",
    "Delgado",
    "Herrera",
    "Morales",
    "Navarro",
]

CARGOS_ADMIN = [
    "Asistente administrativo",
    "Analista administrativo",
    "Especialista en gestión",
    "Auxiliar administrativo",
    "Secretaria académica",
]
CARGOS_DOCENTE_TC = [
    "Docente principal TC",
    "Docente asociado TC",
    "Docente auxiliar TC",
]
CARGOS_DOCENTE_TP = [
    "Docente contratado TP",
    "Docente auxiliar TP",
]

CUENTAS_DEMO = [
    ("admin@utsm.edu.pe", "admin123", "admin", None),
    ("jefe@utsm.edu.pe", "jefe123", "jefe", ("Recursos Humanos", "admin", 0)),
    ("analista@utsm.edu.pe", "analista123", "analista", ("Recursos Humanos", "admin", 1)),
    (
        "coordinador@utsm.edu.pe",
        "coordinador123",
        "coordinador",
        ("Escuela de Administración", "docente_tc", 0),
    ),
    (
        "trabajador@utsm.edu.pe",
        "trabajador123",
        "trabajador",
        ("Escuela de Administración", "docente_tp", 0),
    ),
]


def _nombre_ficticio(indice: int, usados: set[str]) -> str:
    """Genera nombres completos únicos y variados de forma reproducible."""
    posicion = indice % 40
    if posicion % 2 == 0:
        nombre = NOMBRES_FEMENINOS[posicion // 2]
    else:
        nombre = NOMBRES_MASCULINOS[posicion // 2]

    salto = 0
    while True:
        apellido_1 = APELLIDOS[(indice * 7 + salto) % len(APELLIDOS)]
        apellido_2 = APELLIDOS[(indice * 13 + 5 + salto * 3) % len(APELLIDOS)]
        candidato = f"{nombre} {apellido_1} {apellido_2}"
        if candidato not in usados:
            usados.add(candidato)
            return candidato
        salto += 1


def _cargo_para(tipo: str, indice: int) -> str:
    if tipo == "docente_tc":
        return CARGOS_DOCENTE_TC[indice % len(CARGOS_DOCENTE_TC)]
    if tipo == "docente_tp":
        return CARGOS_DOCENTE_TP[indice % len(CARGOS_DOCENTE_TP)]
    return CARGOS_ADMIN[indice % len(CARGOS_ADMIN)]


PATRONES_HORARIO = {
    "admin": (
        (time(7, 30), time(16, 30), "completo"),
        (time(8, 0), time(17, 0), "completo"),
        (time(8, 30), time(17, 30), "completo"),
        (time(9, 0), time(18, 0), "completo"),
        (time(7, 0), time(16, 0), "completo"),
    ),
    "docente_tc": (
        (time(7, 0), time(15, 0), "completo"),
        (time(8, 0), time(16, 0), "completo"),
        (time(10, 0), time(18, 0), "completo"),
        (time(11, 0), time(19, 0), "completo"),
        (time(7, 30), time(15, 30), "completo"),
    ),
    "docente_tp": (
        (time(16, 0), time(21, 0), "parcial"),
        (time(17, 0), time(22, 0), "parcial"),
        (time(18, 0), time(22, 0), "parcial"),
        (time(15, 0), time(20, 0), "parcial"),
    ),
}

FECHA_EMISION_NFC = date(2026, 12, 27)


def _horario_para(tipo: str, indice: int = 0) -> tuple[time, time, str]:
    """Devuelve un turno variado por tipo de personal, no uno único global."""
    patrones = PATRONES_HORARIO.get(tipo, PATRONES_HORARIO["admin"])
    return patrones[indice % len(patrones)]


def _buscar_trabajador(area: str, tipo: str, ocurrencia: int = 0) -> Trabajador | None:
    consulta = (
        Trabajador.query.join(Area)
        .filter(Area.nombre == area, Trabajador.tipo == tipo)
        .order_by(Trabajador.id_trabajador)
    )
    return consulta.offset(ocurrencia).first()


def actualizar_horarios_variados() -> int:
    """Migra una base ya creada a los patrones de horario variados."""
    actualizados = 0
    trabajadores = Trabajador.query.order_by(Trabajador.id_trabajador).all()
    for indice, trabajador in enumerate(trabajadores):
        entrada, salida, turno = _horario_para(trabajador.tipo, indice)
        for horario in trabajador.horarios:
            horario.hora_entrada = entrada
            horario.hora_salida = salida
            horario.tipo_turno = turno
            actualizados += 1
    if actualizados:
        db.session.commit()
    return actualizados


def actualizar_tarjetas_nfc() -> int:
    """Fija la emisión de tarjetas al 27/12/2026 en bases existentes."""
    actualizadas = 0
    for tarjeta in Tarjeta.query.all():
        if tarjeta.fecha_asignacion != FECHA_EMISION_NFC:
            tarjeta.fecha_asignacion = FECHA_EMISION_NFC
            actualizadas += 1
    if actualizadas:
        db.session.commit()
    return actualizadas


def seed_base() -> dict[str, int]:
    """Carga los datos maestros una sola vez (idempotente)."""
    if db.session.query(Sede.id_sede).first():
        return {"existente": True}

    # 1. Sedes ---------------------------------------------------------------
    sedes = [Sede(nombre=nombre, direccion=direccion) for nombre, direccion in SEDES]
    db.session.add_all(sedes)
    db.session.flush()

    # 2. Áreas ---------------------------------------------------------------
    areas: list[Area] = []
    for nombre, indice_sede, _tipo in AREAS:
        area = Area(nombre=nombre, id_sede=sedes[indice_sede].id_sede)
        db.session.add(area)
        areas.append(area)
    db.session.flush()

    areas_admin = [a for a, (_n, _s, tipo) in zip(areas, AREAS, strict=True) if tipo == "admin"]
    areas_docente = [a for a, (_n, _s, tipo) in zip(areas, AREAS, strict=True) if tipo == "docente"]

    # 3. Trabajadores --------------------------------------------------------
    trabajadores: list[Trabajador] = []
    dnis: set[str] = set()
    nombres_usados: set[str] = set()

    def crear_trabajador(tipo: str, area: Area, indice: int) -> Trabajador:
        dni = f"{(41000000 + indice):08d}"
        while dni in dnis:
            indice += 1
            dni = f"{(41000000 + indice):08d}"
        dnis.add(dni)
        trabajador = Trabajador(
            dni=dni,
            nombres=_nombre_ficticio(indice, nombres_usados),
            cargo=_cargo_para(tipo, indice),
            tipo=tipo,
            id_area=area.id_area,
            activo=True,
            fecha_alta=HOY - timedelta(days=random.randint(120, 1500)),
        )
        db.session.add(trabajador)
        trabajadores.append(trabajador)
        return trabajador

    # 120 administrativos distribuidos entre las 7 áreas administrativas
    for i in range(120):
        crear_trabajador("admin", areas_admin[i % len(areas_admin)], i)

    # 80 docentes a tiempo completo entre las 5 escuelas
    for i in range(80):
        crear_trabajador("docente_tc", areas_docente[i % len(areas_docente)], 200 + i)

    # 80 docentes a tiempo parcial
    for i in range(80):
        crear_trabajador("docente_tp", areas_docente[(i + 2) % len(areas_docente)], 400 + i)

    db.session.flush()

    # 4. Tarjetas NFC --------------------------------------------------------
    # La emisión masiva se programa para el 27/12/2026; se usan desde 2027.
    for i, trabajador in enumerate(trabajadores, start=1):
        db.session.add(
            Tarjeta(
                uid=f"UTSM-{i:04d}",
                estado="activa",
                id_trabajador=trabajador.id_trabajador,
                fecha_asignacion=FECHA_EMISION_NFC,
            )
        )

    # 5. Horarios de lunes a viernes, con turnos variados -------------------
    for indice, trabajador in enumerate(trabajadores):
        entrada, salida, turno = _horario_para(trabajador.tipo, indice)
        for dia in range(5):
            db.session.add(
                Horario(
                    id_trabajador=trabajador.id_trabajador,
                    dia_semana=dia,
                    hora_entrada=entrada,
                    hora_salida=salida,
                    tipo_turno=turno,
                )
            )

    # 6. Lectores por sede ---------------------------------------------------
    for sede in sedes:
        for nombre, tipo in (
            ("Entrada principal", "entrada"),
            ("Salida principal", "salida"),
            ("Entrada anexo", "entrada"),
            ("Salida anexo", "salida"),
        ):
            db.session.add(
                Lector(
                    nombre=f"{nombre} · {sede.nombre}",
                    id_sede=sede.id_sede,
                    tipo=tipo,
                    estado="activo",
                )
            )

    db.session.flush()

    # 7. Usuarios de demostración -------------------------------------------
    for correo, clave, rol, vinculo in CUENTAS_DEMO:
        trabajador_id = None
        if vinculo is not None:
            area_nombre, tipo, ocurrencia = vinculo
            trabajador = _buscar_trabajador(area_nombre, tipo, ocurrencia)
            trabajador_id = trabajador.id_trabajador if trabajador else None

        usuario = Usuario(
            correo=correo,
            rol=rol,
            activo=True,
            id_trabajador=trabajador_id,
        )
        usuario.set_password(clave)
        db.session.add(usuario)

    db.session.commit()

    return {
        "sedes": Sede.query.count(),
        "areas": Area.query.count(),
        "trabajadores": Trabajador.query.count(),
        "tarjetas": Tarjeta.query.count(),
        "horarios": Horario.query.count(),
        "lectores": Lector.query.count(),
        "usuarios": Usuario.query.count(),
    }


if __name__ == "__main__":
    from app import create_app

    aplicacion = create_app()
    with aplicacion.app_context():
        db.create_all()
        resumen = seed_base()
        if resumen.get("existente"):
            print("Los datos base ya estaban cargados. No se duplicó nada.")
        else:
            print("Datos base cargados:")
            for clave, valor in resumen.items():
                print(f"  {clave}: {valor}")
            print("\nCuentas de demostración:")
            for correo, clave, rol, _ in CUENTAS_DEMO:
                print(f"  {rol:12s} {correo:28s} {clave}")
