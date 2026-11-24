"""Datos de demostración para la Fase 3.

Crea una incidencia sin justificar para el trabajador demo y otra con una
justificación pendiente para el coordinador de Administración.

Uso:
    .venv/bin/python scripts/demo_fase3.py
    # o: make demo-fase3
"""

import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.kiosk.service import registrar_marcacion  # noqa: E402
from app.models import (  # noqa: E402
    Area,
    Incidencia,
    Justificacion,
    Lector,
    Trabajador,
    Usuario,
)


def main() -> int:
    aplicacion = create_app()
    with aplicacion.app_context():
        if Incidencia.query.count() > 0:
            print("Ya existen incidencias. Reinicia la base o usa la app para continuar.")
            return 0

        usuario_trabajador = Usuario.query.filter_by(correo="trabajador@utsm.edu.pe").first()
        usuario_coordinador = Usuario.query.filter_by(correo="coordinador@utsm.edu.pe").first()
        if not usuario_trabajador or not usuario_trabajador.trabajador:
            print("No se encontró el trabajador demo. Ejecuta el seed base.")
            return 1

        trabajador = usuario_trabajador.trabajador
        coordinador_trabajador = usuario_coordinador.trabajador if usuario_coordinador else None
        excluidos = {trabajador.id_trabajador}
        if coordinador_trabajador is not None:
            excluidos.add(coordinador_trabajador.id_trabajador)

        otro = next(
            (
                candidato
                for candidato in Trabajador.query.join(Area)
                .filter(Area.nombre == "Escuela de Administración")
                .order_by(Trabajador.id_trabajador)
                .all()
                if candidato.id_trabajador not in excluidos and candidato.tarjeta
            ),
            None,
        )
        if otro is None:
            print("No se encontró un segundo trabajador de Administración.")
            return 1

        lector = (
            Lector.query.filter_by(tipo="salida", estado="activo")
            .order_by(Lector.id_lector)
            .first()
        )

        ahora = datetime.now()
        registrar_marcacion(
            trabajador.tarjeta.uid,
            "salida",
            lector.id_lector,
            ahora=ahora,
        )
        incidencia_trabajador = Incidencia.query.order_by(Incidencia.id_incidencia.desc()).first()

        registrar_marcacion(
            otro.tarjeta.uid,
            "salida",
            lector.id_lector,
            ahora=ahora,
        )
        incidencia_coordinador = Incidencia.query.order_by(Incidencia.id_incidencia.desc()).first()

        carpeta = Path(aplicacion.config["UPLOAD_FOLDER"])
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = f"demo_{uuid4().hex[:8]}.pdf"
        (carpeta / archivo).write_bytes(b"%PDF-1.4\n% Sustento de demostracion ShauLA EFC\n")
        justificacion = Justificacion(
            motivo=(
                "El lector de salida no respondió y la marcación quedó observada. "
                "Adjunto el reporte de soporte del equipo."
            ),
            archivo=archivo,
            archivo_original="sustento_demo.pdf",
            estado="enviada",
            fecha_envio=datetime.now(),
            incidencia=incidencia_coordinador,
        )
        db.session.add(justificacion)
        db.session.commit()

        print("Datos de demostración de Fase 3 creados:")
        print(
            f"  Trabajador {trabajador.nombres}: incidencia "
            f"{incidencia_trabajador.id_incidencia} (sin justificar)"
        )
        print(
            f"  Trabajador {otro.nombres}: incidencia "
            f"{incidencia_coordinador.id_incidencia} (justificación pendiente)"
        )
        print("  Abre el panel como trabajador o coordinador para verlas.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
