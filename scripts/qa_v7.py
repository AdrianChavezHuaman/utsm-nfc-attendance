"""Capturas definitivas para gestion_v7.

Requiere el servidor local en http://127.0.0.1:5000.

Uso:
    make run                # en otra terminal
    make shots-v7

Las imágenes se guardan en docs/capturas/v7/ junto con MANIFIESTO.md, que
propone la leyenda APA de cada figura para el anexo del documento.
"""

import shutil
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from selenium import webdriver  # noqa: E402
from selenium.webdriver.common.by import By  # noqa: E402
from selenium.webdriver.firefox.options import Options  # noqa: E402
from selenium.webdriver.support import expected_conditions as EC  # noqa: E402
from selenium.webdriver.support.ui import WebDriverWait  # noqa: E402

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Auditoria, Marca, Usuario  # noqa: E402

BASE = "http://127.0.0.1:5000"
SALIDA = Path("/tmp/opencode/shaula_v7")
DESTINO = PROJECT_ROOT / "docs/capturas/v7"
ESPERA = 20
PAUSA = 0.8

TRABAJADOR = 205
TRABAJADOR_MARCA = 1388673
INCIDENCIA_PENDIENTE = 184748

# archivo, título de la figura, qué muestra, uso sugerido
CAPTURAS = [
    (
        "01_login",
        "Acceso al prototipo",
        "Formulario de acceso con el aviso de sesión y las credenciales de demostración",
        "Cuerpo, seguridad",
    ),
    (
        "02_kiosco",
        "Kiosco NFC",
        "Pantalla de marcación con tarjeta, sede y lector",
        "Cuerpo, TO-BE",
    ),
    (
        "03_inicio",
        "Panel de inicio",
        "Estado del prototipo, datos maestros y cobertura del flujo",
        "Cuerpo, solución",
    ),
    (
        "04_dashboard_2024",
        "Indicadores 2024",
        "Línea base AS-IS con huella dactilar",
        "Cuerpo, diagnóstico",
    ),
    (
        "05_dashboard_2026",
        "Indicadores 2026",
        "Línea base previa al cambio de tecnología",
        "Cuerpo, diagnóstico",
    ),
    (
        "06_dashboard_2027",
        "Indicadores 2027",
        "Meta TO-BE y enero simulado con NFC",
        "Cuerpo, evaluación",
    ),
    (
        "07_asistencia",
        "Asistencia diaria",
        "Tablero del día con estados, horarios e incidencias",
        "Cuerpo, operación",
    ),
    (
        "08_ficha",
        "Ficha individual",
        "Calendario mensual del trabajador con horario y marcas",
        "Cuerpo, operación",
    ),
    ("09_ficha_lista", "Ficha en lista", "Detalle diario de la ficha individual", "Anexo"),
    (
        "10_mi_asistencia",
        "Vista del trabajador",
        "El trabajador consulta su propia asistencia",
        "Cuerpo, roles",
    ),
    (
        "11_incidencia_detalle",
        "Detalle de una incidencia",
        "Estado, plazo y trazabilidad de un caso con el plazo vencido",
        "Cuerpo, justificaciones",
    ),
    (
        "12_justificacion_detalle",
        "Justificación recibida",
        "Sustento digital y decisión del coordinador",
        "Cuerpo, justificaciones",
    ),
    (
        "13_bandeja",
        "Bandeja del coordinador",
        "Casos del área pendientes de revisión",
        "Cuerpo, aprobaciones",
    ),
    (
        "14_horarios",
        "Horarios semanales",
        "Una fila por trabajador con su horario vigente",
        "Cuerpo, operación",
    ),
    (
        "15_horario_semana",
        "Editor de horario",
        "Edición de la semana de un trabajador",
        "Cuerpo, operación",
    ),
    (
        "16_preconsolidado",
        "Preconsolidado mensual",
        "Resumen del mes y excepciones por corregir",
        "Cuerpo, cierre",
    ),
    (
        "17_cierre",
        "Cierre del periodo",
        "Autorización del cierre y archivos generados",
        "Cuerpo, cierre",
    ),
    (
        "18_anual",
        "Consolidado anual",
        "Matriz enero–diciembre y comparativas del caso",
        "Cuerpo, evaluación",
    ),
    ("19_anual_s1", "Vista semestral", "Primer semestre con totales propios", "Cuerpo, evaluación"),
    (
        "20_marcas",
        "Marcaciones del mes",
        "Listado con sede, lector e incidencia",
        "Cuerpo, corrección",
    ),
    (
        "21_corregir_marca",
        "Corrección de una marcación",
        "Formulario con fecha, hora, tipo y motivo",
        "Cuerpo, corrección",
    ),
    (
        "22_auditoria",
        "Auditoría de accesos",
        "Inicios de sesión, intentos fallidos y bloqueos con usuario e IP",
        "Anexo, trazabilidad",
    ),
    (
        "23_auditoria_correccion",
        "Detalle de una corrección",
        "Lectura humana y cambios antes/después",
        "Cuerpo, trazabilidad",
    ),
    (
        "24_auditoria_bloqueo",
        "Detalle de un bloqueo",
        "Cuenta bloqueada por intentos fallidos",
        "Cuerpo, seguridad",
    ),
    ("25_admin_usuarios", "Administración de usuarios", "Cuentas, roles y estado", "Anexo"),
    (
        "26_login_bloqueado",
        "Acceso bloqueado",
        "Mensaje único tras agotar los intentos",
        "Cuerpo, seguridad",
    ),
    (
        "27_sesion_expirada",
        "Sesión expirada",
        "Aviso de cierre por inactividad",
        "Cuerpo, seguridad",
    ),
    ("28_movil_asistencia", "Asistencia en móvil", "Tablero diario en 390 px", "Anexo"),
    ("29_movil_ficha", "Ficha en móvil", "Calendario individual en 390 px", "Anexo"),
    ("30_movil_anual", "Consolidado en móvil", "Vista semestral en 390 px", "Anexo"),
    ("31_movil_marcas", "Marcaciones en móvil", "Listado y acción fija en 390 px", "Anexo"),
]


def crear_driver() -> webdriver.Firefox:
    opciones = Options()
    opciones.add_argument("-headless")
    opciones.set_preference("intl.accept_languages", "es-PE,es")
    opciones.set_preference("general.useragent.locale", "es-PE")
    opciones.set_preference("intl.locale.requested", "es-PE")
    opciones.set_preference("privacy.spoof_english", 0)
    return webdriver.Firefox(options=opciones)


def ir(driver, ruta: str) -> None:
    driver.get(f"{BASE}{ruta}")
    WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "contenido")))


def login(driver, correo: str, clave: str) -> None:
    ir(driver, "/login")
    campo = WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
    campo.clear()
    campo.send_keys(correo)
    contrasena = driver.find_element(By.ID, "password")
    contrasena.clear()
    contrasena.send_keys(clave)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))


def salir(driver) -> None:
    driver.delete_all_cookies()


def capturar(driver, nombre: str, ancho: int = 1440, alto: int = 1200) -> None:
    driver.set_window_size(ancho, alto)
    time.sleep(PAUSA)
    desborde = driver.execute_script(
        "return document.documentElement.scrollWidth - document.documentElement.clientWidth;"
    )
    estado = "OK" if desborde <= 1 else f"DESBORDE {desborde}px"
    print(f"  {nombre}: {estado}")
    driver.save_screenshot(str(SALIDA / f"{nombre}.png"))


def _id_ultimo_evento(accion: str) -> int | None:
    aplicacion = create_app()
    with aplicacion.app_context():
        evento = (
            Auditoria.query.filter_by(accion=accion).order_by(Auditoria.id_evento.desc()).first()
        )
        return evento.id_evento if evento else None


def _id_evento_correccion() -> int | None:
    """Devuelve el evento de la corrección, no el de la restitución posterior."""
    aplicacion = create_app()
    with aplicacion.app_context():
        eventos = (
            Auditoria.query.filter_by(accion="CORREGIR_MARCA")
            .order_by(Auditoria.id_evento.desc())
            .limit(2)
            .all()
        )
        if not eventos:
            return None
        return eventos[1].id_evento if len(eventos) == 2 else eventos[0].id_evento


def _restaurar_marca() -> None:
    aplicacion = create_app()
    with aplicacion.app_context():
        marca = db.session.get(Marca, TRABAJADOR_MARCA)
        if marca is not None:
            marca.fecha_hora = marca.fecha_hora.replace(hour=16, minute=3, second=0)
            db.session.commit()


def _restaurar_cuenta(correo: str) -> None:
    aplicacion = create_app()
    with aplicacion.app_context():
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario is not None:
            usuario.intentos_fallidos = 0
            usuario.bloqueado_hasta = None
            db.session.commit()


def corregir_marca(driver) -> None:
    """Corrige una marca, captura el formulario y restituye el valor original."""
    ir(driver, f"/personal/{TRABAJADOR}/marcas/{TRABAJADOR_MARCA}/corregir")
    hora = driver.find_element(By.ID, "hora")
    driver.execute_script(
        "arguments[0].value = '16:04';"
        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
        hora,
    )
    motivo = driver.find_element(By.ID, "motivo")
    motivo.clear()
    motivo.send_keys("El lector registró la marcación con un minuto de diferencia.")
    capturar(driver, "21_corregir_marca")
    driver.find_element(By.ID, "submit").click()
    WebDriverWait(driver, ESPERA).until(EC.url_contains("/marcas"))

    ir(driver, f"/personal/{TRABAJADOR}/marcas/{TRABAJADOR_MARCA}/corregir")
    hora = driver.find_element(By.ID, "hora")
    driver.execute_script(
        "arguments[0].value = '16:03';"
        "arguments[0].dispatchEvent(new Event('input', {bubbles: true}));",
        hora,
    )
    motivo = driver.find_element(By.ID, "motivo")
    motivo.clear()
    motivo.send_keys("Se verificó la marcación y se restituye la hora original.")
    driver.find_element(By.ID, "submit").click()
    WebDriverWait(driver, ESPERA).until(EC.url_contains("/marcas"))
    _restaurar_marca()


def bloquear_cuenta(driver) -> None:
    """Agota los intentos de una cuenta y captura el mensaje único."""
    salir(driver)
    for _ in range(5):
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        driver.find_element(By.ID, "correo").send_keys("trabajador@utsm.edu.pe")
        driver.find_element(By.ID, "password").send_keys("incorrecta")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".flash"))
        )

    driver.get(f"{BASE}/login")
    WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
    driver.find_element(By.ID, "correo").send_keys("trabajador@utsm.edu.pe")
    driver.find_element(By.ID, "password").send_keys("trabajador123")
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".flash")))
    capturar(driver, "26_login_bloqueado", alto=1000)
    _restaurar_cuenta("trabajador@utsm.edu.pe")


def capturar_expirada(driver) -> None:
    """Renderiza el aviso de inactividad y lo captura desde un archivo local."""
    aplicacion = create_app()
    aplicacion.config["WTF_CSRF_ENABLED"] = False
    cliente = aplicacion.test_client()
    cliente.post(
        "/login",
        data={"correo": "admin@utsm.edu.pe", "password": "admin123"},
    )
    with cliente.session_transaction() as sesion:
        sesion["ultimo_movimiento"] = (datetime.now() - timedelta(minutes=31)).isoformat()
    respuesta = cliente.get("/inicio", follow_redirects=True)
    html = respuesta.get_data(as_text=True)
    html = html.replace("<head>", '<head><base href="http://127.0.0.1:5000/">', 1)
    archivo = SALIDA / "sesion_expirada.html"
    archivo.write_text(html, encoding="utf-8")
    driver.set_window_size(1440, 1000)
    driver.get(archivo.as_uri())
    time.sleep(PAUSA)
    driver.save_screenshot(str(SALIDA / "27_sesion_expirada.png"))
    archivo.unlink(missing_ok=True)
    print("  27_sesion_expirada: OK")


def escribir_manifiesto() -> None:
    lineas = [
        "# Capturas para gestion_v7",
        "",
        "Generadas con `make shots-v7` sobre el prototipo local con datos ficticios.",
        "Las imágenes se proponen para el **Anexo A** del documento, con numeración APA.",
        "",
        "Formato de leyenda:",
        "",
        "> **Figura A1**",
        "> *Acceso al prototipo*",
        "> *Nota.* Fuente: elaboración propia con datos ficticios del prototipo (2026).",
        "",
        "| Figura | Archivo | Qué muestra | Uso sugerido |",
        "| --- | --- | --- | --- |",
    ]
    for indice, (archivo, titulo, detalle, uso) in enumerate(CAPTURAS, start=1):
        lineas.append(f"| A{indice} | `{archivo}.png` | {titulo}. {detalle}. | {uso} |")
    lineas += [
        "",
        "## Notas de uso",
        "",
        "- Las capturas 28 a 31 son de 390 px; las demás de 1440 px.",
        "- Las figuras del cuerpo pueden reutilizar estas imágenes con otra numeración;",
        "  el anexo conserva la serie A1–A31.",
        "- La captura 26 usa la misma frase de error que cualquier fallo de acceso, por",
        "  diseño: el sistema no revela si el correo existe.",
        "- La captura 23 corresponde a una corrección real y su restitución, registradas",
        "  en la auditoría del prototipo.",
        "",
    ]
    (SALIDA / "MANIFIESTO.md").write_text("\n".join(lineas), encoding="utf-8")


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    for archivo in SALIDA.glob("*.png"):
        archivo.unlink()

    driver = crear_driver()
    try:
        # 1. Público
        ir(driver, "/login")
        capturar(driver, "01_login", alto=1000)
        ir(driver, "/kiosk")
        capturar(driver, "02_kiosco", alto=1000)

        # 2. Trabajador
        login(driver, "trabajador@utsm.edu.pe", "trabajador123")
        ir(driver, "/mi-asistencia")
        capturar(driver, "10_mi_asistencia")
        ir(driver, f"/incidencias/{INCIDENCIA_PENDIENTE}")
        capturar(driver, "11_incidencia_detalle")
        salir(driver)

        # 3. Coordinador
        login(driver, "coordinador@utsm.edu.pe", "coordinador123")
        ir(driver, "/bandeja-coordinador")
        capturar(driver, "13_bandeja", alto=700)
        ir(driver, "/incidencias/184111")
        capturar(driver, "12_justificacion_detalle")
        salir(driver)

        # 4. Analista
        login(driver, "analista@utsm.edu.pe", "analista123")
        ir(driver, "/preconsolidado?anio=2026&mes=12")
        capturar(driver, "16_preconsolidado")
        ir(driver, "/consolidado-anual?anio=2026")
        capturar(driver, "18_anual")
        ir(driver, "/consolidado-anual?anio=2026&vista=s1")
        capturar(driver, "19_anual_s1")
        salir(driver)

        # 5. Jefe
        login(driver, "jefe@utsm.edu.pe", "jefe123")
        ir(driver, "/cierre?anio=2026&mes=12")
        capturar(driver, "17_cierre")
        salir(driver)

        # 6. Administrador
        login(driver, "admin@utsm.edu.pe", "admin123")
        ir(driver, "/inicio")
        capturar(driver, "03_inicio")
        ir(driver, "/dashboard?anio=2024")
        capturar(driver, "04_dashboard_2024")
        ir(driver, "/dashboard?anio=2026")
        capturar(driver, "05_dashboard_2026")
        ir(driver, "/dashboard?anio=2027")
        capturar(driver, "06_dashboard_2027")
        ir(driver, "/asistencia?fecha=2026-12-03")
        capturar(driver, "07_asistencia")
        ir(driver, f"/personal/{TRABAJADOR}?anio=2026&mes=12")
        capturar(driver, "08_ficha")
        ir(driver, f"/personal/{TRABAJADOR}?anio=2026&mes=12&vista=lista")
        capturar(driver, "09_ficha_lista")
        ir(driver, "/admin/horarios")
        capturar(driver, "14_horarios")
        ir(driver, f"/admin/horarios/{TRABAJADOR}/semana")
        capturar(driver, "15_horario_semana")
        ir(driver, f"/personal/{TRABAJADOR}/marcas?anio=2026&mes=12")
        capturar(driver, "20_marcas")
        corregir_marca(driver)
        evento_correccion = _id_evento_correccion()

        ir(driver, "/auditoria?tabla=usuario")
        capturar(driver, "22_auditoria")
        if evento_correccion:
            ir(driver, f"/auditoria/{evento_correccion}")
            capturar(driver, "23_auditoria_correccion")
        ir(driver, "/admin/usuarios")
        capturar(driver, "25_admin_usuarios")
        salir(driver)

        # 7. Bloqueo de cuenta y su rastro en auditoría
        bloquear_cuenta(driver)
        evento_bloqueo = _id_ultimo_evento("LOGIN_BLOQUEADO")

        login(driver, "admin@utsm.edu.pe", "admin123")
        if evento_bloqueo:
            ir(driver, f"/auditoria/{evento_bloqueo}")
            capturar(driver, "24_auditoria_bloqueo")

        # 8. Móvil
        ir(driver, "/asistencia?fecha=2026-12-03")
        capturar(driver, "28_movil_asistencia", ancho=390, alto=844)
        ir(driver, f"/personal/{TRABAJADOR}?anio=2026&mes=12")
        capturar(driver, "29_movil_ficha", ancho=390, alto=844)
        ir(driver, "/consolidado-anual?anio=2026&vista=s1")
        capturar(driver, "30_movil_anual", ancho=390, alto=844)
        ir(driver, f"/personal/{TRABAJADOR}/marcas?anio=2026&mes=12")
        capturar(driver, "31_movil_marcas", ancho=390, alto=844)

        # 9. Sesión expirada
        capturar_expirada(driver)
    finally:
        driver.quit()

    escribir_manifiesto()

    if DESTINO.exists():
        shutil.rmtree(DESTINO)
    shutil.copytree(SALIDA, DESTINO)
    print(f"\nCapturas de la Fase 9 copiadas a {DESTINO}")
    print(f"Manifiesto: {DESTINO / 'MANIFIESTO.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
