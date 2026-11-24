"""CRUD de catálogos, tarjetas, lectores y usuarios."""

from datetime import date, datetime, time

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from ..auth.policy import errores_password
from ..extensions import db
from ..kiosk.rules import (
    PLAZO_JUSTIFICACION_DIAS,
    TOLERANCIA_ENTRADA_MIN,
    VENTANA_DOS_SEDES,
    VENTANA_DUPLICADO,
)
from ..models import (
    Area,
    Auditoria,
    Horario,
    Lector,
    Marca,
    Sede,
    Tarjeta,
    Trabajador,
    Usuario,
)
from ..utils.audit import registrar_auditoria
from . import admin_bp
from .registry import ENTIDADES, ENTIDADES_POR_SLUG, TIPOS_TRABAJADOR, Campo

DIAS_FORM = (
    (0, "Lunes"),
    (1, "Martes"),
    (2, "Miércoles"),
    (3, "Jueves"),
    (4, "Viernes"),
    (5, "Sábado"),
)

REGLAS = (
    ("R-01", "Una tarjeta activa pertenece a un solo trabajador.", "Restricción única en tarjeta"),
    (
        "R-02",
        "Duplicado dentro de la ventana de 2 minutos.",
        f"{int(VENTANA_DUPLICADO.total_seconds() // 60)} minutos",
    ),
    (
        "R-03",
        "Tolerancia de entrada antes de marcar la incidencia.",
        f"{TOLERANCIA_ENTRADA_MIN} minutos",
    ),
    ("R-04", "Salida sin entrada o entrada sin salida genera incidencia.", "Automático"),
    ("R-05", "Plazo para presentar la justificación.", f"{PLAZO_JUSTIFICACION_DIAS} días hábiles"),
    ("R-06", "El coordinador solo aprueba su área.", "Validado por permisos"),
    ("R-07", "El jefe autoriza el cierre; después no se edita.", "Periodo bloqueado"),
    ("R-08", "Tarjeta perdida se bloquea de inmediato.", "Estado bloqueada"),
    (
        "R-09",
        "Dos sedes en menos de 30 minutos generan alerta.",
        f"{int(VENTANA_DOS_SEDES.total_seconds() // 60)} minutos",
    ),
    ("R-10", "Se conserva la hora real aunque se sincronice después.", "Hora del evento"),
)


@admin_bp.before_request
def _solo_admin():
    if not current_user.is_authenticated:
        return redirect(url_for("auth.login", next=request.full_path))
    if current_user.rol != "admin":
        abort(403)


def _entidad(slug: str):
    entidad = ENTIDADES_POR_SLUG.get(slug)
    if entidad is None:
        abort(404)
    return entidad


def _opciones(campo: Campo) -> list[tuple[str, str]]:
    if callable(campo.opciones):
        return campo.opciones()
    return list(campo.opciones or [])


def _valores(entidad, objeto=None) -> dict:
    valores = {}
    for campo in entidad.campos:
        if campo.tipo == "password":
            valores[campo.nombre] = ""
            continue
        valor = getattr(objeto, campo.nombre, None) if objeto is not None else None
        if objeto is None:
            valor = campo.default() if callable(campo.default) else campo.default
        if isinstance(valor, (date, datetime)):
            valor = valor.strftime("%Y-%m-%d")
        elif isinstance(valor, time):
            valor = valor.strftime("%H:%M")
        elif valor is None:
            valor = ""
        valores[campo.nombre] = valor
    return valores


def _parsear(entidad, objeto=None) -> tuple[dict, dict]:
    valores, errores = {}, {}
    for campo in entidad.campos:
        crudo = request.form.get(campo.nombre, "").strip()
        if campo.tipo == "checkbox":
            valores[campo.nombre] = campo.nombre in request.form
            continue
        if campo.tipo == "password":
            if not crudo and objeto is None:
                errores[campo.nombre] = "La contraseña es obligatoria al crear la cuenta."
            elif crudo:
                fallas = errores_password(crudo)
                if fallas:
                    errores[campo.nombre] = " ".join(fallas)
            valores[campo.nombre] = crudo
            continue
        if not crudo:
            if campo.requerido:
                errores[campo.nombre] = "Este campo es obligatorio."
            valores[campo.nombre] = None if campo.tipo in {"select_int", "date", "time"} else ""
            continue
        try:
            if campo.tipo == "select_int":
                valores[campo.nombre] = int(crudo)
            elif campo.tipo == "date":
                valores[campo.nombre] = datetime.strptime(crudo, "%Y-%m-%d").date()
            elif campo.tipo == "time":
                valores[campo.nombre] = datetime.strptime(crudo, "%H:%M").time()
            else:
                valores[campo.nombre] = crudo
        except ValueError:
            errores[campo.nombre] = "El valor no tiene un formato válido."
    return valores, errores


def _aplicar(entidad, objeto, valores: dict) -> None:
    for campo in entidad.campos:
        if campo.tipo == "password":
            continue
        setattr(objeto, campo.nombre, valores.get(campo.nombre))
    if isinstance(objeto, Usuario):
        objeto.correo = (valores.get("correo") or "").lower()
        objeto.id_trabajador = valores.get("id_trabajador") or None
        if valores.get("password"):
            objeto.set_password(valores["password"])
    elif isinstance(objeto, Tarjeta):
        objeto.id_trabajador = valores.get("id_trabajador")
    elif isinstance(objeto, Horario):
        objeto.id_trabajador = valores.get("id_trabajador")


def _motivo_bloqueo(objeto) -> str | None:
    """Evita eliminar registros con historia o dependencias."""
    if isinstance(objeto, Usuario) and objeto.id_usuario == current_user.id_usuario:
        return "No puedes eliminar la cuenta con la que estás trabajando."
    if isinstance(objeto, Sede):
        marcas = Marca.query.filter_by(id_sede=objeto.id_sede).count()
        if objeto.areas or objeto.lectores or marcas:
            return "La sede tiene áreas, lectores o marcaciones asociadas."
    if isinstance(objeto, Area) and objeto.trabajadores:
        return "El área tiene trabajadores asignados."
    if isinstance(objeto, Trabajador):
        if objeto.marcas.count() or objeto.incidencias.count():
            return "El trabajador tiene marcaciones o incidencias registradas."
        if objeto.usuario and objeto.usuario.auditorias.count():
            return "Su cuenta de usuario tiene eventos de auditoría."
    if isinstance(objeto, Lector):
        if Marca.query.filter_by(id_lector=objeto.id_lector).count():
            return "El lector tiene marcaciones asociadas."
    if isinstance(objeto, Usuario):
        if objeto.auditorias.count():
            return "La cuenta tiene eventos de auditoría."
        if Auditoria.query.filter_by(id_usuario=objeto.id_usuario).count():
            return "La cuenta tiene eventos de auditoría."
    return None


def _snapshot(entidad, objeto) -> dict:
    datos = {}
    for campo in entidad.campos:
        if campo.tipo == "password":
            continue
        valor = getattr(objeto, campo.nombre, None)
        if isinstance(valor, (date, datetime, time)):
            valor = valor.isoformat()
        datos[campo.nombre] = valor
    return datos


def _auditar(accion: str, entidad, objeto, antes=None, despues=None, commit=True) -> None:
    registrar_auditoria(
        accion,
        entidad.modelo.__tablename__,
        getattr(objeto, entidad.pk),
        datos_anteriores=antes,
        datos_nuevos=despues,
        id_usuario=current_user.id_usuario,
        commit=commit,
    )


def _campos_vista(entidad, valores, errores) -> list[dict]:
    campos = []
    for campo in entidad.campos:
        opciones = _opciones(campo)
        campos.append(
            {
                "campo": campo,
                "opciones": opciones,
                "valor": valores.get(campo.nombre, ""),
                "error": errores.get(campo.nombre),
            }
        )
    return campos


@admin_bp.route("/admin")
def index():
    conteos = {
        "sedes": Sede.query.count(),
        "areas": Area.query.count(),
        "trabajadores": Trabajador.query.filter_by(activo=True).count(),
        "tarjetas": Tarjeta.query.filter_by(estado="activa").count(),
        "horarios": Trabajador.query.filter(Trabajador.horarios.any()).count(),
        "lectores": Lector.query.filter_by(estado="activo").count(),
        "usuarios": Usuario.query.filter_by(activo=True).count(),
    }
    return render_template(
        "admin/index.html",
        entidades=ENTIDADES,
        conteos=conteos,
        reglas=REGLAS,
    )


def _horario_resumen(semana: list[dict]) -> str:
    laborables = [dia["horario"] for dia in semana if dia["laborable"]]
    if not laborables:
        return "Sin horario"
    patrones = {(item["texto"], item["turno"]) for item in laborables}
    if len(patrones) == 1:
        return f"{laborables[0]['texto']} · {laborables[0]['turno']}"
    return "Horario variable"


def _semana_formulario(trabajador: Trabajador) -> list[dict]:
    existentes = {horario.dia_semana: horario for horario in trabajador.horarios}
    semana = []
    for dia, nombre in DIAS_FORM:
        horario = existentes.get(dia)
        semana.append(
            {
                "dia": dia,
                "nombre": nombre,
                "activo": horario is not None,
                "entrada": horario.hora_entrada.strftime("%H:%M") if horario else "08:00",
                "salida": horario.hora_salida.strftime("%H:%M") if horario else "17:00",
                "turno": horario.tipo_turno if horario else "completo",
            }
        )
    return semana


def _horario_snapshot(trabajador: Trabajador) -> dict:
    return {
        horario.dia_semana: [
            horario.hora_entrada.strftime("%H:%M"),
            horario.hora_salida.strftime("%H:%M"),
            horario.tipo_turno,
        ]
        for horario in trabajador.horarios
    }


def _leer_semana_formulario() -> tuple[dict, dict]:
    valores = {}
    errores = {}
    for dia, nombre in DIAS_FORM:
        activo = request.form.get(f"dia_{dia}_activo") == "1"
        if not activo:
            valores[dia] = None
            continue
        entrada_texto = request.form.get(f"dia_{dia}_entrada", "").strip()
        salida_texto = request.form.get(f"dia_{dia}_salida", "").strip()
        turno = request.form.get(f"dia_{dia}_turno", "completo")
        try:
            entrada = datetime.strptime(entrada_texto, "%H:%M").time()
            salida = datetime.strptime(salida_texto, "%H:%M").time()
        except ValueError:
            errores[nombre] = "Completa una hora de entrada y salida válidas."
            valores[dia] = None
            continue
        if salida <= entrada:
            errores[nombre] = "La salida debe ser posterior a la entrada."
            valores[dia] = None
            continue
        valores[dia] = {"entrada": entrada, "salida": salida, "turno": turno}
    return valores, errores


@admin_bp.route("/admin/horarios")
def horarios_lista():
    q = request.args.get("q", "").strip()
    area_id = request.args.get("area", type=int)
    tipo = request.args.get("tipo", "").strip()
    consulta = (
        Trabajador.query.options(
            joinedload(Trabajador.area),
            selectinload(Trabajador.horarios),
        )
        .join(Area, Trabajador.id_area == Area.id_area)
        .filter(Trabajador.activo.is_(True))
    )
    if area_id:
        consulta = consulta.filter(Trabajador.id_area == area_id)
    if tipo:
        consulta = consulta.filter(Trabajador.tipo == tipo)
    if q:
        consulta = consulta.filter(
            or_(Trabajador.nombres.ilike(f"%{q}%"), Trabajador.dni.ilike(f"%{q}%"))
        )
    paginacion = consulta.order_by(Trabajador.nombres).paginate(
        page=request.args.get("pagina", 1, type=int),
        per_page=15,
        error_out=False,
    )
    filas = []
    for trabajador in paginacion.items:
        horarios = {horario.dia_semana: horario for horario in trabajador.horarios}
        semana = []
        for dia, nombre in DIAS_FORM:
            horario = horarios.get(dia)
            semana.append(
                {
                    "dia": dia,
                    "nombre": nombre,
                    "laborable": horario is not None,
                    "horario": {
                        "texto": (
                            f"{horario.hora_entrada:%H:%M}–{horario.hora_salida:%H:%M}"
                            if horario
                            else "—"
                        ),
                        "turno": horario.tipo_turno.capitalize() if horario else "—",
                    },
                }
            )
        filas.append(
            {
                "trabajador": trabajador,
                "nombre_corto": trabajador.nombre_corto,
                "area": trabajador.area.nombre,
                "tipo": dict(TIPOS_TRABAJADOR).get(trabajador.tipo, trabajador.tipo),
                "semana": semana,
                "resumen": _horario_resumen(semana),
            }
        )
    return render_template(
        "admin/horarios_lista.html",
        filas=filas,
        paginacion=paginacion,
        q=q,
        area_id=area_id,
        tipo=tipo,
        opciones=opciones_admin_horarios(),
        query_args={
            "q": q,
            "area": area_id,
            "tipo": tipo,
        },
    )


@admin_bp.route("/admin/horarios/<int:trabajador_id>/semana", methods=["GET", "POST"])
def horarios_semana(trabajador_id: int):
    trabajador = db.session.get(Trabajador, trabajador_id)
    if trabajador is None:
        abort(404)
    errores = {}
    semana = _semana_formulario(trabajador)
    if request.method == "POST":
        valores, errores = _leer_semana_formulario()
        if not errores:
            antes = _horario_snapshot(trabajador)
            existentes = {horario.dia_semana: horario for horario in trabajador.horarios}
            try:
                for dia, valor in valores.items():
                    horario = existentes.get(dia)
                    if valor is None:
                        if horario is not None:
                            db.session.delete(horario)
                        continue
                    if horario is None:
                        horario = Horario(id_trabajador=trabajador.id_trabajador, dia_semana=dia)
                        db.session.add(horario)
                    horario.hora_entrada = valor["entrada"]
                    horario.hora_salida = valor["salida"]
                    horario.tipo_turno = valor["turno"]
                db.session.commit()
                registrar_auditoria(
                    "HORARIO_ACTUALIZADO",
                    "horario",
                    trabajador.id_trabajador,
                    datos_anteriores=antes,
                    datos_nuevos=_horario_snapshot(trabajador),
                    id_usuario=current_user.id_usuario,
                )
                flash(f"Horario semanal de {trabajador.nombre_corto} actualizado.", "success")
                return redirect(url_for("admin.horarios_lista"))
            except IntegrityError:
                db.session.rollback()
                errores["__general__"] = "No se pudo guardar: hay un día duplicado."
            except Exception:
                db.session.rollback()
                errores["__general__"] = "No se pudo guardar el horario."
        for dia in semana:
            dia["activo"] = valores.get(dia["dia"]) is not None
            if dia["activo"]:
                dia["entrada"] = valores[dia["dia"]]["entrada"].strftime("%H:%M")
                dia["salida"] = valores[dia["dia"]]["salida"].strftime("%H:%M")
                dia["turno"] = valores[dia["dia"]]["turno"]
    return render_template(
        "admin/horarios_semana.html",
        trabajador=trabajador,
        semana=semana,
        errores=errores,
    )


def opciones_admin_horarios() -> dict:
    return {
        "areas": Area.query.order_by(Area.nombre).all(),
        "tipos": TIPOS_TRABAJADOR,
    }


@admin_bp.route("/admin/<slug>")
def lista(slug: str):
    if slug == "horarios":
        return redirect(url_for("admin.horarios_lista"))
    entidad = _entidad(slug)
    q = request.args.get("q", "").strip()
    consulta = entidad.modelo.query
    if q and entidad.buscar:
        condiciones = [
            getattr(entidad.modelo, campo).ilike(f"%{q}%")
            for campo in entidad.buscar
            if hasattr(entidad.modelo, campo)
        ]
        if condiciones:
            consulta = consulta.filter(or_(*condiciones))
    consulta = consulta.order_by(getattr(entidad.modelo, entidad.orden))
    paginacion = consulta.paginate(
        page=request.args.get("pagina", 1, type=int),
        per_page=15,
        error_out=False,
    )
    return render_template(
        "admin/lista.html",
        entidad=entidad,
        registros=paginacion.items,
        paginacion=paginacion,
        q=q,
        query_args={"q": q},
    )


@admin_bp.route("/admin/<slug>/nuevo", methods=["GET", "POST"])
def nuevo(slug: str):
    entidad = _entidad(slug)
    errores = {}
    valores = _valores(entidad)
    if request.method == "POST":
        valores, errores = _parsear(entidad)
        if not errores:
            objeto = entidad.modelo()
            _aplicar(entidad, objeto, valores)
            db.session.add(objeto)
            try:
                db.session.flush()
                _auditar(
                    "ADMIN_CREAR",
                    entidad,
                    objeto,
                    despues=_snapshot(entidad, objeto),
                    commit=False,
                )
                db.session.commit()
                flash(f"{entidad.singular} creado correctamente.", "success")
                return redirect(url_for("admin.lista", slug=slug))
            except IntegrityError:
                db.session.rollback()
                errores["__general__"] = "Ya existe un registro con ese valor único."
            except Exception:
                db.session.rollback()
                errores["__general__"] = "No se pudo guardar el registro."
    return render_template(
        "admin/formulario.html",
        entidad=entidad,
        campos=_campos_vista(entidad, valores, errores),
        errores=errores,
        valores=valores,
        es_edicion=False,
    )


@admin_bp.route("/admin/<slug>/<int:objeto_id>/editar", methods=["GET", "POST"])
def editar(slug: str, objeto_id: int):
    entidad = _entidad(slug)
    objeto = db.session.get(entidad.modelo, objeto_id)
    if objeto is None:
        abort(404)
    errores = {}
    valores = _valores(entidad, objeto)
    antes = _snapshot(entidad, objeto)
    if request.method == "POST":
        valores, errores = _parsear(entidad, objeto)
        if not errores:
            _aplicar(entidad, objeto, valores)
            try:
                db.session.flush()
                _auditar(
                    "ADMIN_EDITAR",
                    entidad,
                    objeto,
                    antes=antes,
                    despues=_snapshot(entidad, objeto),
                    commit=False,
                )
                db.session.commit()
                flash(f"{entidad.singular} actualizado correctamente.", "success")
                return redirect(url_for("admin.lista", slug=slug))
            except IntegrityError:
                db.session.rollback()
                errores["__general__"] = "Ya existe un registro con ese valor único."
            except Exception:
                db.session.rollback()
                errores["__general__"] = "No se pudo guardar el registro."
    return render_template(
        "admin/formulario.html",
        entidad=entidad,
        campos=_campos_vista(entidad, valores, errores),
        errores=errores,
        valores=valores,
        es_edicion=True,
        objeto=objeto,
    )


@admin_bp.route("/admin/<slug>/<int:objeto_id>/eliminar", methods=["GET", "POST"])
def eliminar(slug: str, objeto_id: int):
    entidad = _entidad(slug)
    objeto = db.session.get(entidad.modelo, objeto_id)
    if objeto is None:
        abort(404)

    motivo = _motivo_bloqueo(objeto)
    resumen = [(etiqueta, valor(objeto)) for etiqueta, valor in entidad.columnas]

    if request.method == "POST":
        if motivo:
            flash(motivo, "error")
            return redirect(url_for("admin.lista", slug=slug))
        antes = _snapshot(entidad, objeto)
        registro_id = getattr(objeto, entidad.pk)
        try:
            db.session.delete(objeto)
            registrar_auditoria(
                "ADMIN_ELIMINAR",
                entidad.modelo.__tablename__,
                registro_id,
                datos_anteriores=antes,
                id_usuario=current_user.id_usuario,
            )
            flash(f"{entidad.singular} eliminado correctamente.", "success")
        except Exception:
            db.session.rollback()
            flash("No se pudo eliminar el registro por sus dependencias.", "error")
        return redirect(url_for("admin.lista", slug=slug))

    return render_template(
        "admin/eliminar.html",
        entidad=entidad,
        objeto=objeto,
        motivo=motivo,
        resumen=resumen,
    )


@admin_bp.route("/admin/reglas")
def reglas():
    return render_template("admin/reglas.html", reglas=REGLAS)


@admin_bp.post("/admin/lectores/<int:lector_id>/sincronizar")
def sincronizar_lector(lector_id: int):
    lector = db.session.get(Lector, lector_id)
    if lector is None:
        abort(404)
    try:
        registrar_auditoria(
            "LECTOR_SINCRONIZADO",
            "lector",
            lector.id_lector,
            datos_nuevos={"lector": lector.nombre, "estado": "sincronizado"},
            id_usuario=current_user.id_usuario,
        )
        flash(f"Lector {lector.nombre} sincronizado correctamente.", "success")
    except Exception:
        flash("No se pudo registrar la sincronización.", "error")
    return redirect(url_for("admin.lista", slug="lectores"))
