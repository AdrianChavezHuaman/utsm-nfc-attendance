"""Capturas de la Fase 6 con la línea base histórica cargada.

Requiere el servidor local encendido en http://127.0.0.1:5000.

Uso:
    .venv/bin/python scripts/qa_fase6.py
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
SALIDA = Path("/tmp/opencode/shaula_shots_fase6")
DESTINO = Path(__file__).resolve().parent.parent / "docs/capturas/fase6"
ESPERA = 15
PAUSA = 1.0


def capturar(driver: webdriver.Firefox, nombre: str) -> None:
    time.sleep(PAUSA)
    destino = SALIDA / f"{nombre}.png"
    driver.save_screenshot(str(destino))
    print(f"  captura: {destino}")


def sin_desborde(driver: webdriver.Firefox, etiqueta: str) -> None:
    desborde = driver.execute_script(
        "return document.documentElement.scrollWidth - document.documentElement.clientWidth;"
    )
    print(f"  {etiqueta}: {'OK' if desborde <= 1 else f'DESBORDE {desborde}px'}")


def iniciar_sesion(driver, correo: str, clave: str) -> None:
    driver.get(f"{BASE}/login")
    WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
    driver.find_element(By.ID, "correo").clear()
    driver.find_element(By.ID, "correo").send_keys(correo)
    driver.find_element(By.ID, "password").clear()
    driver.find_element(By.ID, "password").send_keys(clave)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))


def esperar_dashboard(driver) -> None:
    WebDriverWait(driver, ESPERA).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
    )
    WebDriverWait(driver, ESPERA).until(
        lambda d: d.execute_script("return document.querySelector('#chart-historico').width > 100")
    )
    time.sleep(PAUSA)


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    DESTINO.mkdir(parents=True, exist_ok=True)
    for archivo in SALIDA.glob("*.png"):
        archivo.unlink()

    opciones = Options()
    opciones.add_argument("-headless")
    opciones.add_argument("--width=1440")
    opciones.add_argument("--height=1000")
    driver = webdriver.Firefox(options=opciones)
    driver.set_window_size(1440, 1000)

    try:
        # 1. Login
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        capturar(driver, "01_login")

        # 2. Panel e dashboard histórico como admin
        iniciar_sesion(driver, "admin@utsm.edu.pe", "admin123")
        driver.get(f"{BASE}/inicio")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "19_inicio_fase6")

        driver.get(f"{BASE}/dashboard?anio=2024")
        esperar_dashboard(driver)
        sin_desborde(driver, "dashboard 2024")
        capturar(driver, "02_dashboard_2024")

        driver.get(f"{BASE}/dashboard?anio=2025")
        esperar_dashboard(driver)
        capturar(driver, "03_dashboard_2025")

        driver.get(f"{BASE}/dashboard?anio=2026&mes=9")
        esperar_dashboard(driver)
        sin_desborde(driver, "dashboard 2026-09")
        capturar(driver, "04_dashboard_2026_linea")

        for tipo, nombre in (
            ("bar", "05_dashboard_2026_barras"),
            ("area", "06_dashboard_2026_area"),
            ("radial", "07_dashboard_2026_radial"),
            ("heatmap", "08_dashboard_2026_heatmap"),
        ):
            Select(driver.find_element(By.ID, "chart-type")).select_by_value(tipo)
            if tipo == "heatmap":
                WebDriverWait(driver, ESPERA).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, "#heatmap-historico .heatmap-cell")
                    )
                )
            time.sleep(PAUSA)
            capturar(driver, nombre)
        errores = driver.find_elements(By.CSS_SELECTOR, ".chart-error")
        print(f"  errores de gráfico: {len(errores)}")

        driver.set_window_size(1440, 1500)
        driver.get(f"{BASE}/dashboard?anio=2026&mes=9")
        esperar_dashboard(driver)
        capturar(driver, "09_dashboard_full")
        driver.set_window_size(1440, 1000)

        # 3. Historial y consolidado
        driver.get(f"{BASE}/periodos")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".period-table"))
        )
        sin_desborde(driver, "periodos 1440")
        capturar(driver, "10_periodos_historico")

        driver.get(f"{BASE}/preconsolidado?anio=2026&mes=10")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        sin_desborde(driver, "preconsolidado 1440")
        capturar(driver, "11_preconsolidado_octubre")

        driver.get(f"{BASE}/preconsolidado?anio=2026&mes=9")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "11b_preconsolidado_septiembre")

        driver.get(f"{BASE}/incidencias")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "12_incidencias_global")

        driver.get(f"{BASE}/admin")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-tabs"))
        )
        capturar(driver, "13_admin")

        driver.get(f"{BASE}/auditoria")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-table"))
        )
        capturar(driver, "14_auditoria")

        # 4. Kiosco y móvil
        driver.get(f"{BASE}/kiosk")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".kiosk-card"))
        )
        capturar(driver, "15_kiosk")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/dashboard?anio=2026&mes=9")
        esperar_dashboard(driver)
        sin_desborde(driver, "dashboard 390")
        capturar(driver, "16_dashboard_mobile")

        driver.set_window_size(320, 800)
        driver.get(f"{BASE}/dashboard?anio=2026&mes=9")
        esperar_dashboard(driver)
        sin_desborde(driver, "dashboard 320")

        # 5. Bandeja del coordinador
        driver.set_window_size(1440, 1000)
        driver.delete_all_cookies()
        iniciar_sesion(driver, "coordinador@utsm.edu.pe", "coordinador123")
        driver.get(f"{BASE}/bandeja-coordinador")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        sin_desborde(driver, "bandeja 1440")
        capturar(driver, "17_bandeja_coordinador")

        # 6. Cierre del jefe (sin ejecutar la acción)
        driver.delete_all_cookies()
        iniciar_sesion(driver, "jefe@utsm.edu.pe", "jefe123")
        driver.get(f"{BASE}/cierre?anio=2026&mes=10")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        sin_desborde(driver, "cierre 1440")
        capturar(driver, "18_cierre_octubre")

        for archivo in sorted(SALIDA.glob("*.png")):
            shutil.copy2(archivo, DESTINO / archivo.name)
        print(f"Capturas de la Fase 6 copiadas a {DESTINO}.")
        print("QA visual de la Fase 6 completada.")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
