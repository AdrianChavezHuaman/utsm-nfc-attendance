"""Presentación legible de eventos de auditoría para usuarios no técnicos."""

import json
from datetime import datetime

from ..utils.helpers import accion_label, role_label

TABLAS = {
    "auditoria": "Auditoría",
    "usuario": "Usuarios",
    "trabajador": "Trabajadores",
    "tarjeta": "Tarjetas NFC",
    "area": "Áreas",
    "sede": "Sedes",
    "horario": "Horarios",
    "lector": "Lectores NFC",
    "marca": "Marcaciones",
    "incidencia": "Incidencias",
    "justificacion": "Justificaciones",
    "periodo": "Periodos",
    "consolidado": "Consolidados",
    "indicador_periodo": "Indicadores",
    "anual": "Consolidado anual",
}

CAMPOS = {
    "nombre": "Nombre",
    "nombres": "Nombres",
    "direccion": "Dirección",
    "activa": "Sede activa",
    "activo": "Activo",
    "correo": "Correo",
    "rol": "Rol",
    "dni": "DNI",
    "cargo": "Cargo",
    "tipo": "Tipo",
    "id_sede": "Sede",
    "id_area": "Área",
    "id_trabajador": "Trabajador",
    "id_lector": "Lector",
    "id_usuario": "Usuario",
    "estado": "Estado",
    "uid": "UID",
    "fecha_asignacion": "Fecha de asignación",
    "hora_entrada": "Hora de entrada",
    "hora_salida": "Hora de salida",
    "dia_semana": "Día",
    "tipo_turno": "Turno",
    "periodo": "Periodo",
    "total_horas": "Horas",
    "total_incidencias": "Incidencias",
    "total_excepciones": "Excepciones",
    "formato": "Formato",
    "eventos": "Eventos",
    "marcas": "Marcas",
    "incidencias": "Incidencias",
    "sede": "Sede",
    "area": "Área",
    "tipo_marca": "Tipo de marcación",
    "tipo_incidencia": "Tipo de incidencia",
    "nota": "Nota",
    "motivo": "Motivo",
    "fecha_hora": "Fecha y hora",
    "archivo": "Archivo",
    "correo_anterior": "Correo anterior",
    "correo_nuevo": "Correo nuevo",
    "escenario": "Escenario",
    "anual": "Año",
}

ACCIONES = {
    "LOGIN": "Inició sesión en el sistema.",
    "LOGOUT": "Cerró sesión en el sistema.",
    "LOGIN_FALLIDO": "Intentó iniciar sesión con credenciales no válidas.",
    "LOGIN_BLOQUEADO": "La cuenta se bloqueó temporalmente por intentos fallidos.",
    "MARCA_INGRESO": "Registró una marcación de ingreso.",
    "MARCA_SALIDA": "Registró una marcación de salida.",
    "MARCA_DUPLICADA": "Se ignoró un intento de marcación duplicada.",
    "MARCA_RECHAZADA": "Se rechazó una marcación.",
    "JUSTIFICACION_ENVIADA": "Envió una justificación.",
    "JUSTIFICACION_APROBADA": "Aprobó una justificación.",
    "JUSTIFICACION_RECHAZADA": "Rechazó una justificación.",
    "PERIODO_CERRADO": "Cerró un periodo de consolidación.",
    "EXCEPCION_CORREGIDA": "Corrigió una excepción del periodo.",
    "CORREGIR_MARCA": "Corrigió una marcación con motivo registrado.",
    "EXPORTACION": "Exportó información del sistema.",
    "ADMIN_CREAR": "Creó un registro.",
    "ADMIN_EDITAR": "Editó un registro.",
    "ADMIN_ELIMINAR": "Eliminó un registro.",
    "HORARIO_ACTUALIZADO": "Actualizó el horario semanal de un trabajador.",
    "LECTOR_SINCRONIZADO": "Sincronizó un lector NFC.",
    "SEED_HISTORICO": "Cargó la línea base histórica.",
}

FECHAS = {
    "fecha",
    "fecha_hora",
    "fecha_cierre",
    "bloqueado_hasta",
    "fecha_asignacion",
    "fecha_envio",
    "fecha_creacion",
}


def _json(valor):
    if not valor:
        return None
    try:
        return json.loads(valor)
    except (TypeError, ValueError):
        return valor


def _fecha(valor):
    if not isinstance(valor, str):
        return None
    try:
        momento = datetime.fromisoformat(valor.replace("T", " "))
    except ValueError:
        return None
    return momento.strftime("%d/%m/%Y %H:%M")


def _valor(campo: str, valor):
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    if campo in FECHAS:
        formato = _fecha(valor)
        if formato:
            return formato
    if campo == "rol":
        return role_label(str(valor))
    if campo in {"estado", "tipo", "tipo_turno"}:
        texto = str(valor).replace("_", " ")
        if texto == "valida":
            return "Válida"
        return texto.capitalize()
    if isinstance(valor, (dict, list)):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def etiqueta_campo(campo: str) -> str:
    return CAMPOS.get(campo, campo.replace("_", " ").capitalize())


def etiqueta_tabla(tabla: str | None) -> str:
    return TABLAS.get(tabla or "", (tabla or "General").replace("_", " ").capitalize())


def _cambios(antes, despues) -> list[dict]:
    if isinstance(antes, dict) or isinstance(despues, dict):
        antes = antes if isinstance(antes, dict) else {}
        despues = despues if isinstance(despues, dict) else {}
        claves = list(dict.fromkeys([*antes.keys(), *despues.keys()]))
        return [
            {
                "campo": clave,
                "etiqueta": etiqueta_campo(clave),
                "antes": _valor(clave, antes.get(clave)),
                "despues": _valor(clave, despues.get(clave)),
            }
            for clave in claves
            if antes.get(clave) != despues.get(clave)
        ]
    return []


def presentar_evento(evento) -> dict:
    antes = _json(evento.valores_anteriores)
    despues = _json(evento.valores_nuevos)
    resumen = ACCIONES.get(evento.accion, f"{accion_label(evento.accion)}.")
    tabla = etiqueta_tabla(evento.tabla_afectada)

    if evento.accion.startswith("ADMIN_"):
        resumen = f"{resumen[:-1]} de {tabla.lower()}."
    if evento.accion == "PERIODO_CERRADO" and isinstance(despues, dict):
        periodo = despues.get("periodo")
        if periodo:
            resumen = f"Cerró el periodo {periodo} y archivó el consolidado."
    if evento.accion == "EXPORTACION" and isinstance(despues, dict):
        periodo = despues.get("periodo") or despues.get("anual")
        formato = despues.get("formato")
        if periodo:
            resumen = f"Exportó {periodo} en formato {str(formato or 'archivo').upper()}."
    if evento.accion == "SEED_HISTORICO" and isinstance(despues, dict):
        marcas = despues.get("marcas")
        periodos = despues.get("periodos")
        if marcas:
            resumen = f"Cargó {len(periodos or [])} periodos y {marcas:,} marcas históricas."

    cambios = (
        [] if evento.accion in {"LOGIN", "LOGOUT", "LOGIN_FALLIDO"} else _cambios(antes, despues)
    )
    tecnico_antes = json.dumps(antes, ensure_ascii=False, indent=2) if antes else "—"
    tecnico_despues = json.dumps(despues, ensure_ascii=False, indent=2) if despues else "—"
    return {
        "resumen": resumen,
        "tabla": tabla,
        "cambios": cambios,
        "tecnico_antes": tecnico_antes,
        "tecnico_despues": tecnico_despues,
    }
