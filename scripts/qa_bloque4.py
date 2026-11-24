"""Capturas de evidencia del Bloque 4: auditoría, paginación y acabado visual."""

import shutil
import sys
import time
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
from app.models import Auditoria  # noqa: E402

BASE = "http://127.0.0.1:5000"
SALIDA = Path("/tmp/opencode/shaula_bloque4")
DESTINO = Path(__file__).resolve().parent.parent / "docs/capturas/bloque4"
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
    opciones.add_argument("--height=1200")
    driver = webdriver.Firefox(options=opciones)
    driver.set_window_size(1440, 1200)

    aplicacion = create_app()
    with aplicacion.app_context():
        evento = (
            Auditoria.query.filter_by(accion="LECTOR_SINCRONIZADO")
            .order_by(Auditoria.id_evento.desc())
            .first()
        )
        if evento is None:
            evento = Auditoria.query.order_by(Auditoria.id_evento.desc()).first()
        evento_id = evento.id_evento if evento else 1

    try:
        driver.get(f"{BASE}/login")
        WebDriverWait(driver, ESPERA).until(EC.presence_of_element_located((By.ID, "correo")))
        driver.find_element(By.ID, "correo").send_keys("admin@utsm.edu.pe")
        driver.find_element(By.ID, "password").send_keys("admin123")
        driver.find_element(By.CSS_SELECTOR, "button[type=submit]").click()
        WebDriverWait(driver, ESPERA).until(EC.url_contains("/inicio"))

        driver.get(f"{BASE}/auditoria")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-table"))
        )
        sin_desborde(driver, "auditoría 1440")
        capturar(driver, "01_auditoria")

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        capturar(driver, "02_auditoria_paginacion")

        driver.get(f"{BASE}/auditoria/{evento_id}")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-summary-card"))
        )
        capturar(driver, "03_auditoria_detalle")

        driver.get(f"{BASE}/admin/trabajadores")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".admin-tabs"))
        )
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
        sin_desborde(driver, "admin 1440")
        capturar(driver, "04_admin_paginacion")

        driver.get(f"{BASE}/inicio")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".page-head"))
        )
        capturar(driver, "05_inicio_acabado")

        driver.set_window_size(390, 844)
        driver.get(f"{BASE}/auditoria")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-table"))
        )
        sin_desborde(driver, "auditoría 390")
        capturar(driver, "06_auditoria_mobile")

        driver.get(f"{BASE}/auditoria/{evento_id}")
        WebDriverWait(driver, ESPERA).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".audit-summary-card"))
        )
        sin_desborde(driver, "detalle auditoría 390")
        capturar(driver, "07_auditoria_detalle_mobile")

        for archivo in sorted(SALIDA.glob("*.png")):
            shutil.copy2(archivo, DESTINO / archivo.name)
        print(f"Capturas del Bloque 4 copiadas a {DESTINO}.")
        return 0
    finally:
        driver.quit()


if __name__ == "__main__":
    raise SystemExit(main())
