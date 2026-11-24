"""Prueba de humo contra la base real de instance/asistencia.db.

Verifica login con CSRF activo, panel, estáticos, logout y error 404.
Uso:
    .venv/bin/python scripts/smoke_test.py
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402


def extraer_csrf(html: str) -> str:
    coincidencia = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', html)
    if not coincidencia:
        raise SystemExit("No se encontró el token CSRF en el HTML.")
    return coincidencia.group(1)


def main() -> int:
    app = create_app()
    app.config.update(TESTING=True)
    cliente = app.test_client()

    pasos: list[tuple[str, bool, str]] = []

    respuesta = cliente.get("/login")
    pasos.append(("GET /login", respuesta.status_code == 200, str(respuesta.status_code)))
    html = respuesta.get_data(as_text=True)
    token = extraer_csrf(html)

    respuesta = cliente.post(
        "/login",
        data={
            "csrf_token": token,
            "correo": "admin@utsm.edu.pe",
            "password": "admin123",
        },
        follow_redirects=False,
    )
    pasos.append(
        (
            "POST /login (admin)",
            respuesta.status_code == 302 and "/inicio" in respuesta.headers.get("Location", ""),
            str(respuesta.status_code),
        ),
    )

    respuesta = cliente.get("/inicio")
    html = respuesta.get_data(as_text=True)
    pasos.append(("GET /inicio", respuesta.status_code == 200, str(respuesta.status_code)))
    pasos.append(("Panel saluda al usuario", "Hola," in html, "texto presente"))
    pasos.append(("Prototipo operativo", "Prototipo operativo" in html, "badge presente"))
    pasos.append(("Sin restos de Jinja", "{{" not in html and "{%" not in html, "limpio"))

    respuesta = cliente.get("/dashboard")
    html = respuesta.get_data(as_text=True)
    pasos.append(
        (
            "GET /dashboard (admin)",
            respuesta.status_code == 200 and "Oportunidad del cierre" in html,
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/auditoria")
    pasos.append(
        (
            "GET /auditoria (admin)",
            respuesta.status_code == 200
            and "Registro de auditor" in respuesta.get_data(as_text=True),
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/admin")
    pasos.append(
        (
            "GET /admin (admin)",
            respuesta.status_code == 200 and "Administraci" in respuesta.get_data(as_text=True),
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/api/kpi", query_string={"anio": 2027})
    datos = respuesta.get_json(silent=True) or {}
    pasos.append(
        (
            "GET /api/kpi (2027)",
            respuesta.status_code == 200 and datos.get("proyeccion") is True,
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/incidencias")
    pasos.append(
        (
            "GET /incidencias (admin)",
            respuesta.status_code == 200
            and "Incidencias del proceso" in respuesta.get_data(as_text=True),
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/periodos")
    pasos.append(
        (
            "GET /periodos (admin)",
            respuesta.status_code == 200 and "Periodos" in respuesta.get_data(as_text=True),
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/kiosk")
    pasos.append(
        (
            "GET /kiosk",
            respuesta.status_code == 200
            and "Tarjetas de demostración" in respuesta.get_data(as_text=True),
            str(respuesta.status_code),
        )
    )

    for ruta, tipo in (
        ("/static/css/glass.css", "text/css"),
        ("/static/css/app.css", "text/css"),
        ("/static/css/login.css", "text/css"),
        ("/static/css/dashboard.css", "text/css"),
        ("/static/js/app.js", "javascript"),
        ("/static/js/charts.js", "javascript"),
        ("/static/vendor/chart.umd.min.js", "javascript"),
        ("/static/fonts/ManropeVariable.woff2", "font"),
        ("/static/fonts/JetBrainsMonoVariable.woff2", "font"),
    ):
        respuesta = cliente.get(ruta)
        pasos.append(
            (
                f"GET {ruta}",
                respuesta.status_code == 200 and tipo in respuesta.content_type,
                respuesta.content_type,
            ),
        )

    respuesta = cliente.get("/inicio")
    token = extraer_csrf(respuesta.get_data(as_text=True))
    respuesta = cliente.post("/logout", data={"csrf_token": token}, follow_redirects=True)
    pasos.append(
        (
            "POST /logout",
            respuesta.status_code == 200 and "Sesi" in respuesta.get_data(as_text=True),
            str(respuesta.status_code),
        )
    )

    respuesta = cliente.get("/ruta-inexistente")
    pasos.append(
        (
            "404 estilizado",
            respuesta.status_code == 404 and b"no encontrada" in respuesta.data,
            str(respuesta.status_code),
        )
    )

    fallos = 0
    for nombre, ok, detalle in pasos:
        estado = "OK " if ok else "FALLO"
        print(f"[{estado}] {nombre} ({detalle})")
        if not ok:
            fallos += 1

    print(f"\n{len(pasos) - fallos}/{len(pasos)} comprobaciones correctas.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
