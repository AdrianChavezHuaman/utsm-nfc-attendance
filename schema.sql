-- Generado automáticamente desde instance/asistencia.db
-- Fuente de verdad: app/models.py

CREATE TABLE area (
	id_area INTEGER NOT NULL, 
	nombre VARCHAR(150) NOT NULL, 
	id_sede INTEGER NOT NULL, 
	PRIMARY KEY (id_area), 
	FOREIGN KEY(id_sede) REFERENCES sede (id_sede)
);

CREATE TABLE auditoria (
	id_evento INTEGER NOT NULL, 
	fecha DATETIME NOT NULL, 
	accion VARCHAR(60) NOT NULL, 
	tabla_afectada VARCHAR(60), 
	registro_id INTEGER, 
	valores_anteriores TEXT, 
	valores_nuevos TEXT, 
	ip VARCHAR(45), 
	id_usuario INTEGER, 
	PRIMARY KEY (id_evento), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
);

CREATE TABLE consolidado (
	id_consolidado INTEGER NOT NULL, 
	tipo VARCHAR(5) NOT NULL, 
	archivo VARCHAR(300) NOT NULL, 
	fecha_generacion DATETIME NOT NULL, 
	id_periodo INTEGER NOT NULL, 
	id_usuario INTEGER, 
	PRIMARY KEY (id_consolidado), 
	FOREIGN KEY(id_periodo) REFERENCES periodo (id_periodo), 
	FOREIGN KEY(id_usuario) REFERENCES usuario (id_usuario)
);

CREATE TABLE horario (
	id_horario INTEGER NOT NULL, 
	id_trabajador INTEGER NOT NULL, 
	dia_semana INTEGER NOT NULL, 
	hora_entrada TIME NOT NULL, 
	hora_salida TIME NOT NULL, 
	tipo_turno VARCHAR(24) NOT NULL, 
	PRIMARY KEY (id_horario), 
	CONSTRAINT uq_horario_dia UNIQUE (id_trabajador, dia_semana), 
	FOREIGN KEY(id_trabajador) REFERENCES trabajador (id_trabajador)
);

CREATE TABLE incidencia (
	id_incidencia INTEGER NOT NULL, 
	tipo VARCHAR(13) NOT NULL, 
	estado VARCHAR(11) NOT NULL, 
	observacion VARCHAR(300), 
	fecha_creacion DATETIME NOT NULL, 
	id_marca INTEGER NOT NULL, 
	id_trabajador INTEGER NOT NULL, 
	PRIMARY KEY (id_incidencia), 
	UNIQUE (id_marca), 
	FOREIGN KEY(id_marca) REFERENCES marca (id_marca), 
	FOREIGN KEY(id_trabajador) REFERENCES trabajador (id_trabajador)
);

CREATE TABLE indicador_periodo (
	id_indicador INTEGER NOT NULL, 
	anio INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	escenario VARCHAR(24) NOT NULL, 
	oportunidad FLOAT NOT NULL, 
	eficiencia_h FLOAT NOT NULL, 
	calidad_pct FLOAT NOT NULL, 
	extraviadas_pct FLOAT NOT NULL, 
	costo FLOAT NOT NULL, 
	adopcion_nfc FLOAT NOT NULL, 
	fuente VARCHAR(160), 
	nota VARCHAR(300), 
	PRIMARY KEY (id_indicador), 
	CONSTRAINT uq_indicador_anio_mes_escenario UNIQUE (anio, mes, escenario)
);

CREATE TABLE justificacion (
	id_justificacion INTEGER NOT NULL, 
	motivo TEXT NOT NULL, 
	archivo VARCHAR(300), 
	archivo_original VARCHAR(255), 
	estado VARCHAR(9) NOT NULL, 
	fecha_envio DATETIME NOT NULL, 
	fecha_resolucion DATETIME, 
	comentario_resolucion VARCHAR(300), 
	id_incidencia INTEGER NOT NULL, 
	id_usuario_resolvio INTEGER, 
	PRIMARY KEY (id_justificacion), 
	UNIQUE (id_incidencia), 
	FOREIGN KEY(id_incidencia) REFERENCES incidencia (id_incidencia), 
	FOREIGN KEY(id_usuario_resolvio) REFERENCES usuario (id_usuario)
);

CREATE TABLE lector (
	id_lector INTEGER NOT NULL, 
	nombre VARCHAR(80) NOT NULL, 
	id_sede INTEGER NOT NULL, 
	tipo VARCHAR(7) NOT NULL, 
	estado VARCHAR(13) NOT NULL, 
	PRIMARY KEY (id_lector), 
	FOREIGN KEY(id_sede) REFERENCES sede (id_sede)
);

CREATE TABLE marca (
	id_marca INTEGER NOT NULL, 
	fecha_hora DATETIME NOT NULL, 
	tipo VARCHAR(7) NOT NULL, 
	estado VARCHAR(9) NOT NULL, 
	medio VARCHAR(12) NOT NULL, 
	id_trabajador INTEGER NOT NULL, 
	id_lector INTEGER NOT NULL, 
	id_sede INTEGER NOT NULL, 
	PRIMARY KEY (id_marca), 
	FOREIGN KEY(id_trabajador) REFERENCES trabajador (id_trabajador), 
	FOREIGN KEY(id_lector) REFERENCES lector (id_lector), 
	FOREIGN KEY(id_sede) REFERENCES sede (id_sede)
);

CREATE TABLE periodo (
	id_periodo INTEGER NOT NULL, 
	anio INTEGER NOT NULL, 
	mes INTEGER NOT NULL, 
	estado VARCHAR(9) NOT NULL, 
	fecha_cierre DATETIME, 
	id_usuario_cierre INTEGER, 
	total_trabajadores INTEGER NOT NULL, 
	total_horas FLOAT NOT NULL, 
	total_incidencias INTEGER NOT NULL, 
	total_excepciones INTEGER NOT NULL, 
	creado_en DATETIME NOT NULL, escenario VARCHAR(24) NOT NULL DEFAULT 'as_is', 
	PRIMARY KEY (id_periodo), 
	CONSTRAINT uq_periodo_anio_mes UNIQUE (anio, mes), 
	FOREIGN KEY(id_usuario_cierre) REFERENCES usuario (id_usuario)
);

CREATE TABLE sede (
	id_sede INTEGER NOT NULL, 
	nombre VARCHAR(120) NOT NULL, 
	direccion VARCHAR(220), 
	activa BOOLEAN NOT NULL, 
	PRIMARY KEY (id_sede), 
	UNIQUE (nombre)
);

CREATE TABLE tarjeta (
	id_tarjeta INTEGER NOT NULL, 
	uid VARCHAR(24) NOT NULL, 
	estado VARCHAR(9) NOT NULL, 
	id_trabajador INTEGER NOT NULL, 
	fecha_asignacion DATE NOT NULL, 
	PRIMARY KEY (id_tarjeta), 
	UNIQUE (id_trabajador), 
	FOREIGN KEY(id_trabajador) REFERENCES trabajador (id_trabajador)
);

CREATE TABLE trabajador (
	id_trabajador INTEGER NOT NULL, 
	dni VARCHAR(8) NOT NULL, 
	nombres VARCHAR(180) NOT NULL, 
	cargo VARCHAR(120) NOT NULL, 
	tipo VARCHAR(10) NOT NULL, 
	id_area INTEGER NOT NULL, 
	activo BOOLEAN NOT NULL, 
	fecha_alta DATE NOT NULL, 
	PRIMARY KEY (id_trabajador), 
	FOREIGN KEY(id_area) REFERENCES area (id_area)
);

CREATE TABLE usuario (
	id_usuario INTEGER NOT NULL, 
	correo VARCHAR(150) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	rol VARCHAR(11) NOT NULL, 
	activo BOOLEAN NOT NULL, 
	ultimo_acceso DATETIME, 
	id_trabajador INTEGER, 
	intentos_fallidos INTEGER NOT NULL DEFAULT 0, 
	bloqueado_hasta DATETIME, 
	PRIMARY KEY (id_usuario), 
	UNIQUE (id_trabajador), 
	FOREIGN KEY(id_trabajador) REFERENCES trabajador (id_trabajador)
);

CREATE INDEX ix_area_id_sede ON area (id_sede);

CREATE INDEX ix_auditoria_accion ON auditoria (accion);

CREATE INDEX ix_auditoria_fecha ON auditoria (fecha);

CREATE INDEX ix_auditoria_id_usuario ON auditoria (id_usuario);

CREATE INDEX ix_auditoria_tabla_fecha ON auditoria (tabla_afectada, fecha);

CREATE INDEX ix_auditoria_usuario_fecha ON auditoria (id_usuario, fecha);

CREATE INDEX ix_consolidado_id_periodo ON consolidado (id_periodo);

CREATE INDEX ix_horario_trabajador_dia ON horario (id_trabajador, dia_semana);

CREATE INDEX ix_incidencia_estado ON incidencia (estado);

CREATE INDEX ix_incidencia_id_trabajador ON incidencia (id_trabajador);

CREATE INDEX ix_incidencia_tipo ON incidencia (tipo);

CREATE INDEX ix_incidencia_trabajador_estado ON incidencia (id_trabajador, estado);

CREATE INDEX ix_indicador_anio_escenario ON indicador_periodo (anio, escenario);

CREATE INDEX ix_indicador_periodo_anio ON indicador_periodo (anio);

CREATE INDEX ix_indicador_periodo_escenario ON indicador_periodo (escenario);

CREATE INDEX ix_justificacion_estado ON justificacion (estado);

CREATE INDEX ix_lector_id_sede ON lector (id_sede);

CREATE INDEX ix_lector_tipo ON lector (tipo);

CREATE INDEX ix_marca_fecha_hora ON marca (fecha_hora);

CREATE INDEX ix_marca_fecha_trabajador ON marca (fecha_hora, id_trabajador);

CREATE INDEX ix_marca_id_sede ON marca (id_sede);

CREATE INDEX ix_marca_id_trabajador ON marca (id_trabajador);

CREATE INDEX ix_marca_sede_fecha ON marca (id_sede, fecha_hora);

CREATE INDEX ix_periodo_escenario ON periodo (escenario);

CREATE INDEX ix_periodo_estado ON periodo (estado);

CREATE INDEX ix_tarjeta_estado ON tarjeta (estado);

CREATE UNIQUE INDEX ix_tarjeta_uid ON tarjeta (uid);

CREATE UNIQUE INDEX ix_trabajador_dni ON trabajador (dni);

CREATE INDEX ix_trabajador_id_area ON trabajador (id_area);

CREATE INDEX ix_trabajador_tipo ON trabajador (tipo);

CREATE UNIQUE INDEX ix_usuario_correo ON usuario (correo);

CREATE INDEX ix_usuario_rol ON usuario (rol);
