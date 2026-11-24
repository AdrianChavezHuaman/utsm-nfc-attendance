"""Modelo de datos del proceso AP-GTH-01 (control de asistencia).

Entidades alineadas con la Tabla 21 del documento gestion_v6.docx:
sede, area, trabajador, tarjeta, horario, lector, marca, incidencia,
justificacion, usuario, auditoria, periodo, consolidado e indicadores.
"""

from datetime import date, datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

# ---------------------------------------------------------------------------
# Catálogos de valores (se reflejan como CHECK en SQLite)
# ---------------------------------------------------------------------------
TIPOS_TRABAJADOR = ("admin", "docente_tc", "docente_tp")
ESTADOS_TARJETA = ("activa", "bloqueada", "repuesta")
TIPOS_LECTOR = ("entrada", "salida")
ESTADOS_LECTOR = ("activo", "inactivo", "mantenimiento")
TIPOS_MARCA = ("ingreso", "salida")
ESTADOS_MARCA = ("valida", "observada")
MEDIOS_MARCA = ("nfc", "huella", "contingencia")
TIPOS_INCIDENCIA = (
    "falta_entrada",
    "falta_salida",
    "fuera_horario",
    "duplicado",
    "doble_sede",
)
ESTADOS_INCIDENCIA = ("pendiente", "justificada", "rechazada", "cerrada")
ESTADOS_JUSTIFICACION = ("enviada", "aprobada", "rechazada")
ESTADOS_PERIODO = ("abierto", "cerrado", "bloqueado")
ESCENARIOS_PERIODO = ("as_is", "to_be_simulado")
TIPOS_CONSOLIDADO = ("csv", "excel", "pdf")
ROLES_USUARIO = ("trabajador", "coordinador", "analista", "jefe", "admin")

MESES_LARGOS = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)


class Sede(db.Model):
    """Sede física de la universidad."""

    __tablename__ = "sede"

    id_sede = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False, unique=True)
    direccion = db.Column(db.String(220))
    activa = db.Column(db.Boolean, nullable=False, default=True)

    areas = db.relationship("Area", back_populates="sede", lazy="selectin")
    lectores = db.relationship("Lector", back_populates="sede", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Sede {self.nombre}>"


class Area(db.Model):
    """Área o escuela profesional a la que pertenece el trabajador."""

    __tablename__ = "area"

    id_area = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    id_sede = db.Column(db.Integer, db.ForeignKey("sede.id_sede"), nullable=False, index=True)

    sede = db.relationship("Sede", back_populates="areas")
    trabajadores = db.relationship("Trabajador", back_populates="area", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Area {self.nombre}>"


class Trabajador(db.Model):
    """Personal docente o administrativo registrado en el sistema."""

    __tablename__ = "trabajador"

    id_trabajador = db.Column(db.Integer, primary_key=True)
    dni = db.Column(db.String(8), nullable=False, unique=True, index=True)
    nombres = db.Column(db.String(180), nullable=False)
    cargo = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.Enum(*TIPOS_TRABAJADOR, name="tipo_trabajador"), nullable=False, index=True)
    id_area = db.Column(db.Integer, db.ForeignKey("area.id_area"), nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    fecha_alta = db.Column(db.Date, nullable=False, default=date.today)

    area = db.relationship("Area", back_populates="trabajadores")
    tarjeta = db.relationship(
        "Tarjeta", back_populates="trabajador", uselist=False, cascade="all, delete-orphan"
    )
    horarios = db.relationship(
        "Horario", back_populates="trabajador", cascade="all, delete-orphan", lazy="selectin"
    )
    marcas = db.relationship("Marca", back_populates="trabajador", lazy="dynamic")
    incidencias = db.relationship("Incidencia", back_populates="trabajador", lazy="dynamic")
    usuario = db.relationship(
        "Usuario", back_populates="trabajador", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def nombre_corto(self) -> str:
        return " ".join(self.nombres.split()[:2])

    def __repr__(self) -> str:
        return f"<Trabajador {self.dni} {self.nombre_corto}>"


class Tarjeta(db.Model):
    """Tarjeta NFC asignada a un único trabajador (regla R-01)."""

    __tablename__ = "tarjeta"

    id_tarjeta = db.Column(db.Integer, primary_key=True)
    uid = db.Column(db.String(24), nullable=False, unique=True, index=True)
    estado = db.Column(
        db.Enum(*ESTADOS_TARJETA, name="estado_tarjeta"),
        nullable=False,
        default="activa",
        index=True,
    )
    id_trabajador = db.Column(
        db.Integer,
        db.ForeignKey("trabajador.id_trabajador"),
        nullable=False,
        unique=True,
    )
    fecha_asignacion = db.Column(db.Date, nullable=False, default=date.today)

    trabajador = db.relationship("Trabajador", back_populates="tarjeta")

    def __repr__(self) -> str:
        return f"<Tarjeta {self.uid} ({self.estado})>"


class Horario(db.Model):
    """Turno programado por trabajador y día de la semana (0 = lunes)."""

    __tablename__ = "horario"
    __table_args__ = (
        db.UniqueConstraint("id_trabajador", "dia_semana", name="uq_horario_dia"),
        db.Index("ix_horario_trabajador_dia", "id_trabajador", "dia_semana"),
    )

    id_horario = db.Column(db.Integer, primary_key=True)
    id_trabajador = db.Column(db.Integer, db.ForeignKey("trabajador.id_trabajador"), nullable=False)
    dia_semana = db.Column(db.Integer, nullable=False)  # 0 lunes ... 6 domingo
    hora_entrada = db.Column(db.Time, nullable=False)
    hora_salida = db.Column(db.Time, nullable=False)
    tipo_turno = db.Column(db.String(24), nullable=False, default="completo")

    trabajador = db.relationship("Trabajador", back_populates="horarios")

    def __repr__(self) -> str:
        return (
            f"<Horario t={self.id_trabajador} dia={self.dia_semana} "
            f"{self.hora_entrada}-{self.hora_salida}>"
        )


class Lector(db.Model):
    """Lector NFC físico (o simulado) instalado en una sede."""

    __tablename__ = "lector"

    id_lector = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), nullable=False)
    id_sede = db.Column(db.Integer, db.ForeignKey("sede.id_sede"), nullable=False, index=True)
    tipo = db.Column(db.Enum(*TIPOS_LECTOR, name="tipo_lector"), nullable=False, index=True)
    estado = db.Column(
        db.Enum(*ESTADOS_LECTOR, name="estado_lector"), nullable=False, default="activo"
    )

    sede = db.relationship("Sede", back_populates="lectores")

    def __repr__(self) -> str:
        return f"<Lector {self.nombre} ({self.tipo})>"


class Marca(db.Model):
    """Evento de marcación (ingreso o salida) de un trabajador."""

    __tablename__ = "marca"
    __table_args__ = (
        db.Index("ix_marca_fecha_trabajador", "fecha_hora", "id_trabajador"),
        db.Index("ix_marca_sede_fecha", "id_sede", "fecha_hora"),
    )

    id_marca = db.Column(db.Integer, primary_key=True)
    fecha_hora = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    tipo = db.Column(db.Enum(*TIPOS_MARCA, name="tipo_marca"), nullable=False)
    estado = db.Column(
        db.Enum(*ESTADOS_MARCA, name="estado_marca"), nullable=False, default="valida"
    )
    medio = db.Column(db.Enum(*MEDIOS_MARCA, name="medio_marca"), nullable=False, default="nfc")
    id_trabajador = db.Column(
        db.Integer,
        db.ForeignKey("trabajador.id_trabajador"),
        nullable=False,
        index=True,
    )
    id_lector = db.Column(db.Integer, db.ForeignKey("lector.id_lector"), nullable=False)
    id_sede = db.Column(db.Integer, db.ForeignKey("sede.id_sede"), nullable=False, index=True)

    trabajador = db.relationship("Trabajador", back_populates="marcas")
    lector = db.relationship("Lector")
    sede = db.relationship("Sede")
    incidencia = db.relationship(
        "Incidencia",
        back_populates="marca",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Marca {self.fecha_hora:%Y-%m-%d %H:%M} t={self.id_trabajador} {self.tipo}>"


class Incidencia(db.Model):
    """Marcación observada o faltante que requiere revisión."""

    __tablename__ = "incidencia"
    __table_args__ = (db.Index("ix_incidencia_trabajador_estado", "id_trabajador", "estado"),)

    id_incidencia = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum(*TIPOS_INCIDENCIA, name="tipo_incidencia"), nullable=False, index=True)
    estado = db.Column(
        db.Enum(*ESTADOS_INCIDENCIA, name="estado_incidencia"),
        nullable=False,
        default="pendiente",
        index=True,
    )
    observacion = db.Column(db.String(300))
    fecha_creacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    id_marca = db.Column(
        db.Integer,
        db.ForeignKey("marca.id_marca"),
        nullable=False,
        unique=True,
    )
    id_trabajador = db.Column(
        db.Integer,
        db.ForeignKey("trabajador.id_trabajador"),
        nullable=False,
        index=True,
    )

    marca = db.relationship("Marca", back_populates="incidencia")
    trabajador = db.relationship("Trabajador", back_populates="incidencias")
    justificacion = db.relationship(
        "Justificacion",
        back_populates="incidencia",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Incidencia {self.tipo} ({self.estado})>"


class Justificacion(db.Model):
    """Sustento digital presentado por el trabajador para una incidencia."""

    __tablename__ = "justificacion"

    id_justificacion = db.Column(db.Integer, primary_key=True)
    motivo = db.Column(db.Text, nullable=False)
    archivo = db.Column(db.String(300))
    archivo_original = db.Column(db.String(255))
    estado = db.Column(
        db.Enum(*ESTADOS_JUSTIFICACION, name="estado_justificacion"),
        nullable=False,
        default="enviada",
        index=True,
    )
    fecha_envio = db.Column(db.DateTime, nullable=False, default=datetime.now)
    fecha_resolucion = db.Column(db.DateTime)
    comentario_resolucion = db.Column(db.String(300))
    id_incidencia = db.Column(
        db.Integer,
        db.ForeignKey("incidencia.id_incidencia"),
        nullable=False,
        unique=True,
    )
    id_usuario_resolvio = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=True)

    incidencia = db.relationship("Incidencia", back_populates="justificacion")
    usuario_resolvio = db.relationship("Usuario", back_populates="justificaciones_resueltas")

    @property
    def nombre_archivo(self) -> str | None:
        return self.archivo_original or self.archivo

    def __repr__(self) -> str:
        return f"<Justificacion {self.id_justificacion} ({self.estado})>"


class Usuario(UserMixin, db.Model):
    """Cuenta de acceso al sistema con uno de los cinco roles del proceso."""

    __tablename__ = "usuario"

    id_usuario = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(150), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    rol = db.Column(db.Enum(*ROLES_USUARIO, name="rol_usuario"), nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    ultimo_acceso = db.Column(db.DateTime)
    intentos_fallidos = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    bloqueado_hasta = db.Column(db.DateTime)
    id_trabajador = db.Column(
        db.Integer,
        db.ForeignKey("trabajador.id_trabajador"),
        nullable=True,
        unique=True,
    )

    trabajador = db.relationship("Trabajador", back_populates="usuario")
    auditorias = db.relationship("Auditoria", back_populates="usuario", lazy="dynamic")
    justificaciones_resueltas = db.relationship(
        "Justificacion", back_populates="usuario_resolvio", lazy="dynamic"
    )

    # -- Contraseñas --------------------------------------------------------
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # -- Bloqueo por intentos fallidos -------------------------------------
    def esta_bloqueado(self, ahora: datetime | None = None) -> bool:
        """Indica si la cuenta sigue dentro del bloqueo temporal."""
        if not self.bloqueado_hasta:
            return False
        return self.bloqueado_hasta > (ahora or datetime.now())

    def registrar_intento_fallido(self, max_intentos: int, minutos: int) -> bool:
        """Suma un fallo y bloquea la cuenta al llegar al máximo.

        Devuelve True si la cuenta quedó bloqueada en este intento.
        """
        ahora = datetime.now()
        if self.bloqueado_hasta and self.bloqueado_hasta <= ahora:
            self.bloqueado_hasta = None
            self.intentos_fallidos = 0
        self.intentos_fallidos = (self.intentos_fallidos or 0) + 1
        if self.intentos_fallidos >= max_intentos:
            self.bloqueado_hasta = ahora + timedelta(minutes=minutos)
            return True
        return False

    def reiniciar_intentos(self) -> None:
        """Limpia el contador cuando el acceso es correcto."""
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None

    # -- Flask-Login --------------------------------------------------------
    def get_id(self) -> str:
        return str(self.id_usuario)

    @property
    def is_active(self) -> bool:
        return self.activo

    @property
    def nombre_visible(self) -> str:
        return self.trabajador.nombres if self.trabajador else "Administrador del sistema"

    @property
    def nombre_corto(self) -> str:
        """Nombre compacto para barras y cabeceras."""
        return self.trabajador.nombre_corto if self.trabajador else "Admin. UTSM"

    def __repr__(self) -> str:
        return f"<Usuario {self.correo} ({self.rol})>"


class Periodo(db.Model):
    """Periodo mensual de consolidación y su estado de cierre."""

    __tablename__ = "periodo"
    __table_args__ = (
        db.UniqueConstraint("anio", "mes", name="uq_periodo_anio_mes"),
        db.Index("ix_periodo_estado", "estado"),
    )

    id_periodo = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False)
    mes = db.Column(db.Integer, nullable=False)
    estado = db.Column(
        db.Enum(*ESTADOS_PERIODO, name="estado_periodo"),
        nullable=False,
        default="abierto",
    )
    escenario = db.Column(db.String(24), nullable=False, default="as_is", index=True)
    fecha_cierre = db.Column(db.DateTime)
    id_usuario_cierre = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=True)
    total_trabajadores = db.Column(db.Integer, nullable=False, default=0)
    total_horas = db.Column(db.Float, nullable=False, default=0.0)
    total_incidencias = db.Column(db.Integer, nullable=False, default=0)
    total_excepciones = db.Column(db.Integer, nullable=False, default=0)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.now)

    usuario_cierre = db.relationship("Usuario")
    consolidados = db.relationship(
        "Consolidado",
        back_populates="periodo",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def etiqueta(self) -> str:
        return f"{MESES_LARGOS[self.mes - 1]} {self.anio}"

    @property
    def es_simulacion(self) -> bool:
        return self.escenario == "to_be_simulado"

    def __repr__(self) -> str:
        return f"<Periodo {self.anio}-{self.mes:02d} ({self.estado})>"


class IndicadorPeriodo(db.Model):
    """Indicadores del caso por año o mes y por escenario AS-IS/TO-BE."""

    __tablename__ = "indicador_periodo"
    __table_args__ = (
        db.UniqueConstraint("anio", "mes", "escenario", name="uq_indicador_anio_mes_escenario"),
        db.Index("ix_indicador_anio_escenario", "anio", "escenario"),
    )

    id_indicador = db.Column(db.Integer, primary_key=True)
    anio = db.Column(db.Integer, nullable=False, index=True)
    # mes = 0 significa valor anual; 1-12 es el mes concreto.
    mes = db.Column(db.Integer, nullable=False, default=0)
    escenario = db.Column(db.String(24), nullable=False, default="as_is", index=True)
    oportunidad = db.Column(db.Float, nullable=False, default=0.0)
    eficiencia_h = db.Column(db.Float, nullable=False, default=0.0)
    calidad_pct = db.Column(db.Float, nullable=False, default=0.0)
    extraviadas_pct = db.Column(db.Float, nullable=False, default=0.0)
    costo = db.Column(db.Float, nullable=False, default=0.0)
    adopcion_nfc = db.Column(db.Float, nullable=False, default=0.0)
    fuente = db.Column(db.String(160))
    nota = db.Column(db.String(300))

    @property
    def etiqueta(self) -> str:
        if self.mes:
            return f"{MESES_LARGOS[self.mes - 1]} {self.anio}"
        return f"Año {self.anio}"

    def __repr__(self) -> str:
        return f"<IndicadorPeriodo {self.anio}-{self.mes:02d} {self.escenario}>"


class Consolidado(db.Model):
    """Archivo generado para un periodo (CSV, Excel o PDF)."""

    __tablename__ = "consolidado"

    id_consolidado = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.Enum(*TIPOS_CONSOLIDADO, name="tipo_consolidado"), nullable=False)
    archivo = db.Column(db.String(300), nullable=False)
    fecha_generacion = db.Column(db.DateTime, nullable=False, default=datetime.now)
    id_periodo = db.Column(
        db.Integer, db.ForeignKey("periodo.id_periodo"), nullable=False, index=True
    )
    id_usuario = db.Column(db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=True)

    periodo = db.relationship("Periodo", back_populates="consolidados")
    usuario = db.relationship("Usuario")

    def __repr__(self) -> str:
        return f"<Consolidado {self.tipo} periodo={self.id_periodo}>"


class Auditoria(db.Model):
    """Registro inmutable de acciones del sistema."""

    __tablename__ = "auditoria"
    __table_args__ = (
        db.Index("ix_auditoria_usuario_fecha", "id_usuario", "fecha"),
        db.Index("ix_auditoria_tabla_fecha", "tabla_afectada", "fecha"),
    )

    id_evento = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    accion = db.Column(db.String(60), nullable=False, index=True)
    tabla_afectada = db.Column(db.String(60))
    registro_id = db.Column(db.Integer)
    valores_anteriores = db.Column(db.Text)
    valores_nuevos = db.Column(db.Text)
    ip = db.Column(db.String(45))
    id_usuario = db.Column(
        db.Integer, db.ForeignKey("usuario.id_usuario"), nullable=True, index=True
    )

    usuario = db.relationship("Usuario", back_populates="auditorias")

    def __repr__(self) -> str:
        return f"<Auditoria {self.fecha:%Y-%m-%d %H:%M} {self.accion}>"
