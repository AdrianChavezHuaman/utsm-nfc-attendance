"""Capturas de control visual con Selenium + Firefox (QA opcional).

Requiere: .venv/bin/pip install selenium
Con el servidor local encendido en http://127.0.0.1:5000.

Uso:
    .venv/bin/python scripts/qa_screenshots.py
"""

import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

BASE = "http://127.0.0.1:5000"
SALIDA = Path("/tmp/opencode/shaula_shots")
CAPTURAS_FASE5 = Path(__file__).resolve().parent.parent / "docs/capturas/fase5"
ESPERA = 12
PAUSA = 0.9


def capturar(driver: webdriver.Firefox, nombre: str) -> None:
    time.sleep(PAUSA)
    destino = SALIDA / f"{nombre}.png"
    driver.save_screenshot(str(destino))
    print(f"  captura: {destino}")


def sin_desborde_horizontal(driver: webdriver.Firefox, etiqueta: str) -> None:
    """Comprueba que la página no desborde a lo ancho."""
    desborde = driver.execute_script(
        "return document.documentElement.scrollWidth - document.documentElement.clientWidth;"
    )
    estado = "OK" if desborde <= 1 else f"DESBORDE {desborde}px"
    print(f"  {etiqueta}: {estado}")


def iniciar_sesion(driver, correo: str = "admin@utsm.edu.pe", clave: str = "admin123") -> None:
    driver.get(f"{BASE}/login")
    WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
    driver.find_element(By.ID, "correo").send_keys(correo)
    driver.find_element(By.ID, "password").send_keys(clave)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)

    opciones = Options()
    opciones.add_argument("-headless")
    opciones.add_argument("--width=1440")
    opciones.add_argument("--height=900")
    driver = webdriver.Firefox(options=opciones)
    driver.set_window_size(1440, 900)

    try:
        # 1. Login escritorio
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        capturar(driver, "01_login_desktop")

        # 2. Error de credenciales
        driver.find_element(By.ID, "correo").send_keys("admin@utsm.edu.pe")
        driver.find_element(By.ID, "password").send_keys("clave-incorrecta")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".flash--error"))
        )
        capturar(driver, "02_login_error")

        # 3. Panel autenticado
        iniciar_sesion(driver)
        WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        sin_desborde_horizontal(driver, "panel 1440")
        capturar(driver, "03_inicio_desktop")

        driver.set_window_size(1440, 1600)
        capturar(driver, "03b_inicio_full")
        driver.set_window_size(1440, 900)

        # 4. Vista móvil del login
        driver.delete_all_cookies()
        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        sin_desborde_horizontal(driver, "login 390")
        capturar(driver, "04_login_mobile")

        driver.find_element(By.CSS_SELECTOR, ".demo-box summary").click()
        capturar(driver, "04b_login_mobile_demo")

        # 5. Panel móvil y menú lateral
        iniciar_sesion(driver)
        WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))
        sin_desborde_horizontal(driver, "panel 390")
        capturar(driver, "05_inicio_mobile")

        driver.set_window_size(390, 1600)
        capturar(driver, "05b_inicio_mobile_full")

        driver.set_window_size(320, 800)
        driver.get(f"{BASE}/inicio")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        sin_desborde_horizontal(driver, "panel 320")
        capturar(driver, "05c_inicio_320")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/inicio")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-sidebar-toggle]"))
        )
        driver.find_element(By.CSS_SELECTOR, "[data-sidebar-toggle]").click()
        WebDriverWait(driver, ESPERA).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, ".sidebar.is-open"))
        )
        capturar(driver, "06_sidebar_mobile")

        # 6. Error 404 y control a 320 px
        driver.set_window_size(320, 800)
        driver.get(f"{BASE}/ruta-inexistente")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".error-card"))
        )
        sin_desborde_horizontal(driver, "error 320")
        capturar(driver, "07_error_mobile")

        # 7. Kiosco de marcación: pantalla, resultado y móvil
        driver.set_window_size(1440, 900)
        driver.get(f"{BASE}/kiosk")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kiosk-card"))
        )
        sin_desborde_horizontal(driver, "kiosco 1440")
        capturar(driver, "08_kiosk_desktop")

        driver.find_element(By.CSS_SELECTOR, ".uid-chip").click()
        driver.find_element(By.CSS_SELECTOR, "[data-kiosk-submit]").click()
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".result"))
        )
        capturar(driver, "09_kiosk_result")

        driver.set_window_size(1440, 1600)
        driver.get(f"{BASE}/inicio")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "11_inicio_after_kiosk")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/kiosk")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kiosk-card"))
        )
        sin_desborde_horizontal(driver, "kiosco 390")
        capturar(driver, "10_kiosk_mobile")

        # 8. Panel KPI: gráficos intercambiables
        driver.set_window_size(1440, 900)
        driver.get(f"{BASE}/dashboard")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
        )
        WebDriverWait(driver, ESPERA).until(
            lambda d: d.execute_script(
                "return document.querySelector('#chart-historico').width > 100"
            )
        )
        sin_desborde_horizontal(driver, "dashboard 1440")
        capturar(driver, "28_dashboard_kpi")

        for tipo, nombre in (
            ("bar", "29_dashboard_barras"),
            ("area", "30_dashboard_area"),
            ("radial", "31_dashboard_radial"),
        ):
            Select(driver.find_element(By.ID, "chart-type")).select_by_value(tipo)
            time.sleep(PAUSA)
            capturar(driver, nombre)

        Select(driver.find_element(By.ID, "chart-type")).select_by_value("heatmap")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#heatmap-historico .heatmap-cell"))
        )
        errores = driver.find_elements(By.CSS_SELECTOR, ".chart-error")
        print(f"  errores de gráfico: {len(errores)}")
        capturar(driver, "32_dashboard_heatmap")

        driver.set_window_size(1440, 1500)
        driver.get(f"{BASE}/dashboard")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
        )
        time.sleep(PAUSA)
        capturar(driver, "33_dashboard_full")
        driver.set_window_size(1440, 900)

        # 9. Proyección 2027
        driver.get(f"{BASE}/dashboard?anio=2027")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
        )
        time.sleep(PAUSA)
        proyeccion = "Proyección TO-BE 2027" in driver.page_source
        print(f"  proyección 2027 visible: {'OK' if proyeccion else 'FALLO'}")
        capturar(driver, "34_dashboard_2027")

        # 10. Panel KPI móvil y 320 px
        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/dashboard")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
        )
        time.sleep(PAUSA)
        sin_desborde_horizontal(driver, "dashboard 390")
        capturar(driver, "35_dashboard_mobile")

        driver.set_window_size(320, 800)
        driver.get(f"{BASE}/dashboard")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
        )
        time.sleep(PAUSA)
        sin_desborde_horizontal(driver, "dashboard 320")

        # 11. Auditoría
        driver.set_window_size(1440, 900)
        driver.get(f"{BASE}/auditoria")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-table"))
        )
        sin_desborde_horizontal(driver, "auditoría 1440")
        capturar(driver, "36_auditoria")

        Select(driver.find_element(By.CSS_SELECTOR, "select[name=accion]")).select_by_value("LOGIN")
        driver.find_element(By.CSS_SELECTOR, ".audit-filters button[type=submit]").click()
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-table"))
        )
        capturar(driver, "37_auditoria_filtrada")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/auditoria")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-filters"))
        )
        sin_desborde_horizontal(driver, "auditoría 390")
        capturar(driver, "38_auditoria_mobile")

        # 12. Administración
        driver.set_window_size(1440, 900)
        driver.get(f"{BASE}/admin")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-tabs"))
        )
        sin_desborde_horizontal(driver, "admin 1440")
        capturar(driver, "39_admin")

        driver.get(f"{BASE}/admin/trabajadores")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-search"))
        )
        capturar(driver, "40_admin_trabajadores")

        driver.get(f"{BASE}/admin/trabajadores/nuevo")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-form"))
        )
        capturar(driver, "41_admin_formulario")

        driver.get(f"{BASE}/admin/reglas")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".rule-table"))
        )
        capturar(driver, "42_admin_reglas")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/admin")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-tabs"))
        )
        sin_desborde_horizontal(driver, "admin 390")
        capturar(driver, "43_admin_mobile")

        CAPTURAS_FASE5.mkdir(parents=True, exist_ok=True)
        for numero in range(28, 44):
            for archivo in sorted(SALIDA.glob(f"{numero}_*.png")):
                shutil.copy2(archivo, CAPTURAS_FASE5 / archivo.name)
        print(f"Capturas de la Fase 5 copiadas a {CAPTURAS_FASE5}.")

        print("QA visual completado sin errores de navegación.")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
