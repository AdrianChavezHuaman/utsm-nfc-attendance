"""Capturas de evidencia del Bloque 1: AS-IS 2024-2026 y TO-BE enero 2027.

Requiere el servidor local en http://127.0.0.1:5000.
Uso:
    .venv/bin/python scripts/qa_bloque1.py
"""

import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:5000"
SALIDA = Path("/tmp/opencode/shaula_bloque1")
DESTINO = Path(__file__).resolve().parent.parent / "docs/capturas/bloque1"
ESPERA = 15
PAUSA = 1.0


def capturar(driver, nombre: str) -> None:
    time.sleep(PAUSA)
    driver.save_screenshot(str(SALIDA / f"{nombre}.png"))
    print(f"  captura: {nombre}")


def sin_desborde(driver, etiqueta: str) -> None:
    desborde = driver.execute_script(
        "return document.documentElement.scrollWidth - document.documentElement.clientWidth;"
    )
    print(f"  {etiqueta}: {'OK' if desborde <= 1 else f'DESBORDE {desborde}px'}")


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
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        driver.find_element(By.ID, "correo").send_keys("admin@utsm.edu.pe")
        driver.find_element(By.ID, "password").send_keys("admin123")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))

        for nombre, ruta in (
            ("01_dashboard_2024_as_is", "/dashboard?anio=2024"),
            ("02_dashboard_2026_as_is", "/dashboard?anio=2026"),
            ("03_dashboard_2027_to_be", "/dashboard?anio=2027"),
        ):
            driver.get(f"{BASE}{ruta}")
            WebDriverWait(driver, ESPERA).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".kpi-card"))
            )
            WebDriverWait(driver, ESPERA).until(
                lambda d: d.execute_script(
                    "return document.querySelector('#chart-historico').width > 100"
                )
            )
            time.sleep(PAUSA)
            sin_desborde(driver, nombre)
            capturar(driver, nombre)

        driver.get(f"{BASE}/periodos")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".period-table"))
        )
        capturar(driver, "04_periodos_2026_2027")

        driver.get(f"{BASE}/preconsolidado?anio=2026&mes=12")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "05_preconsolidado_diciembre_2026")

        driver.get(f"{BASE}/preconsolidado?anio=2027&mes=1")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "06_preconsolidado_enero_2027_simulado")

        driver.get(f"{BASE}/admin/tarjetas")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-tabs"))
        )
        capturar(driver, "07_admin_tarjetas_emision")

        driver.get(f"{BASE}/admin/horarios")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-tabs"))
        )
        capturar(driver, "08_admin_horarios_variados")

        for archivo in sorted(SALIDA.glob("*.png")):
            shutil.copy2(archivo, DESTINO / archivo.name)
        print(f"Capturas del Bloque 1 copiadas a {DESTINO}.")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
