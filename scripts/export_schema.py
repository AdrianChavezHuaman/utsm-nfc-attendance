"""Genera schema.sql a partir de la base SQLite local.

Uso:
    .venv/bin/python scripts/export_schema.py
"""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "instance" / "asistencia.db"
SCHEMA_PATH = PROJECT_ROOT / "schema.sql"


def main() -> int:
    if not DB_PATH.exists():
        print(f"No existe la base: {DB_PATH}")
        print("Ejecuta primero: .venv/bin/flask --app run.py bootstrap")
        return 1

    conexion = sqlite3.connect(DB_PATH)
    filas = conexion.execute(
        """
        SELECT sql FROM sqlite_master
        WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'
        ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name
        """
    ).fetchall()
    conexion.close()

    contenido = ";\n\n".join(fila[0] for fila in filas)
    SCHEMA_PATH.write_text(
        "-- Generado automáticamente desde instance/asistencia.db\n"
        "-- Fuente de verdad: app/models.py\n\n"
        f"{contenido};\n",
        encoding="utf-8",
    )
    print(f"schema.sql actualizado ({len(filas)} objetos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
