"""Capturas de evidencia del Bloque 2: asistencia, personal y horarios."""

import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:5000"
SALIDA = Path("/tmp/opencode/shaula_bloque2")
DESTINO = Path(__file__).resolve().parent.parent / "docs/capturas/bloque2"
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


def login(driver, correo: str, clave: str) -> None:
    driver.get(f"{BASE}/login")
    WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
    driver.find_element(By.ID, "correo").send_keys(correo)
    driver.find_element(By.ID, "password").send_keys(clave)
    driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
    WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))


def main() -> int:
    SALIDA.mkdir(parents=True, exist_ok=True)
    DESTINO.mkdir(parents=True, exist_ok=True)
    for archivo in SALIDA.glob("*.png"):
        archivo.unlink()

    opciones = Options()
    opciones.add_argument("-headless")
    opciones.add_argument("--width=1440")
    opciones.add_argument("--height=1100")
    driver = webdriver.Firefox(options=opciones)
    driver.set_window_size(1440, 1100)

    try:
        login(driver, "admin@utsm.edu.pe", "admin123")

        driver.get(f"{BASE}/asistencia?fecha=2026-10-15")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".attendance-table"))
        )
        sin_desborde(driver, "asistencia 1440")
        capturar(driver, "01_asistencia_diaria")

        driver.get(f"{BASE}/personal")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".personal-table"))
        )
        sin_desborde(driver, "personal 1440")
        capturar(driver, "02_personal_directorio")

        driver.get(f"{BASE}/personal/1")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".attendance-calendar"))
        )
        sin_desborde(driver, "ficha calendario 1440")
        capturar(driver, "03_ficha_calendario")

        driver.get(f"{BASE}/personal/1?vista=lista")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".personal-list-table"))
        )
        capturar(driver, "04_ficha_lista")

        driver.get(f"{BASE}/admin/horarios")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".weekly-admin-table"))
        )
        sin_desborde(driver, "horarios 1440")
        capturar(driver, "05_admin_horarios_semanal")

        driver.get(f"{BASE}/admin/horarios/1/semana")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".schedule-week"))
        )
        capturar(driver, "06_admin_editar_semana")

        driver.set_window_size(390, 844)
        for nombre, ruta, selector in (
            ("07_asistencia_mobile", "/asistencia?fecha=2026-10-15", ".attendance-table"),
            ("08_ficha_mobile", "/personal/1", ".attendance-calendar"),
            ("09_horarios_mobile", "/admin/horarios", ".weekly-admin-table"),
        ):
            driver.get(f"{BASE}{ruta}")
            WebDriverWait(driver, ESPERA).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            sin_desborde(driver, f"{nombre} 390")
            capturar(driver, nombre)
        driver.set_window_size(320, 800)

        driver.delete_all_cookies()
        login(driver, "trabajador@utsm.edu.pe", "trabajador123")
        driver.get(f"{BASE}/mi-asistencia")
        WebDriverWait(driver, ESPERA).until(EC.url_contains("/personal/"))
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".attendance-calendar"))
        )
        sin_desborde(driver, "mi asistencia 320")
        capturar(driver, "10_mi_asistencia")

        for archivo in sorted(SALIDA.glob("*.png")):
            shutil.copy2(archivo, DESTINO / archivo.name)
        print(f"Capturas del Bloque 2 copiadas a {DESTINO}.")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
