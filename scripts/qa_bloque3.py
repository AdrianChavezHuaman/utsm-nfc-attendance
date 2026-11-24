"""Capturas de evidencia del Bloque 3: consolidado anual y comparativas."""

import shutil
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

BASE = "http://127.0.0.1:5000"
SALIDA = Path("/tmp/opencode/shaula_bloque3")
DESTINO = Path(__file__).resolve().parent.parent / "docs/capturas/bloque3"
ESPERA = 20
PAUSA = 1.2


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
    opciones.add_argument("--height=1100")
    driver = webdriver.Firefox(options=opciones)
    driver.set_window_size(1440, 1100)

    try:
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        driver.find_element(By.ID, "correo").send_keys("admin@utsm.edu.pe")
        driver.find_element(By.ID, "password").send_keys("admin123")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))

        driver.get(f"{BASE}/consolidado-anual?anio=2026")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#chart-eneros"))
        )
        time.sleep(1.5)
        sin_desborde(driver, "anual 2026 - 1440")
        capturar(driver, "01_anual_2026")

        driver.execute_script("window.scrollTo(0, 1050)")
        capturar(driver, "02_comparativas_2026")

        driver.get(f"{BASE}/consolidado-anual?anio=2027")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#chart-eneros"))
        )
        time.sleep(1.5)
        capturar(driver, "03_anual_2027")

        driver.get(f"{BASE}/consolidado-anual?anio=2026&tipo=docente_tp")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#chart-eneros"))
        )
        time.sleep(1.5)
        capturar(driver, "04_anual_filtro_tipo")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/consolidado-anual?anio=2026")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#chart-eneros"))
        )
        time.sleep(1.2)
        sin_desborde(driver, "anual 2026 - 390")
        capturar(driver, "05_anual_mobile")

        for archivo in sorted(SALIDA.glob("*.png")):
            shutil.copy2(archivo, DESTINO / archivo.name)
        print(f"Capturas del Bloque 3 copiadas a {DESTINO}.")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
