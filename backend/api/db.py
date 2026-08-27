"""Conexion a la DB local del proyecto -- copia independiente para backend/api/.

Mismo patron de 4 lineas que backend/importer/db.py y backend/scripts/*.py
(Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db",
PRAGMA foreign_keys = ON) -- deliberadamente NO importado de esas carpetas
(fase6-dashboard-basico-sprint-contract.md seccion 3, AGENTS.md seccion 24).
"""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "db" / "tcg_dashboard.db"


def connect(db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def get_db() -> Iterator[sqlite3.Connection]:
    """FastAPI dependency: una conexion nueva por request, cerrada al final (sin pool)."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
