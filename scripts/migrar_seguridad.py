"""Agrega las columnas de seguridad de acceso a la base local.

Uso:
    .venv/bin/python scripts/migrar_seguridad.py
    .venv/bin/python scripts/migrar_seguridad.py --db otra.db

El script es idempotente: si las columnas ya existen, no hace nada.
Antes de modificar el esquema crea un respaldo en instance/backups/.
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "instance" / "asistencia.db"
BACKUP_DIR = PROJECT_ROOT / "instance" / "backups"

COLUMNAS = (
    ("intentos_fallidos", "INTEGER NOT NULL DEFAULT 0"),
    ("bloqueado_hasta", "DATETIME"),
)


def _columnas(conexion: sqlite3.Connection, tabla: str) -> set[str]:
    return {fila[1] for fila in conexion.execute(f"PRAGMA table_info({tabla})")}


def _respaldar(origen: Path) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUP_DIR / f"asistencia_pre_migracion_seguridad_{marca}.db"
    with sqlite3.connect(origen) as fuente, sqlite3.connect(destino) as copia:
        fuente.backup(copia)
    return destino


def migrar(db_path: Path) -> int:
    if not db_path.exists():
        print(f"No existe la base: {db_path}")
        return 1

    with sqlite3.connect(db_path) as conexion:
        existentes = _columnas(conexion, "usuario")
        faltantes = [(nombre, tipo) for nombre, tipo in COLUMNAS if nombre not in existentes]
        if not faltantes:
            print("Sin cambios: las columnas de seguridad ya existen.")
            return 0

        respaldo = _respaldar(db_path)
        print(f"Respaldo: {respaldo}")

        for nombre, tipo in faltantes:
            conexion.execute(f"ALTER TABLE usuario ADD COLUMN {nombre} {tipo}")
            print(f"Columna agregada: usuario.{nombre}")
        conexion.commit()

        finales = _columnas(conexion, "usuario")
        assert all(nombre in finales for nombre, _ in COLUMNAS)
        print("Migración completada.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Migra las columnas de seguridad de acceso.")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Ruta de la base SQLite.")
    argumentos = parser.parse_args()
    return migrar(argumentos.db)


if __name__ == "__main__":
    sys.exit(main())
