"""Helper de tests: DB en memoria con el schema+seed real de Fase 3."""

import sqlite3
from pathlib import Path

DB_SQL_DIR = Path(__file__).resolve().parent.parent / "db"


def make_test_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript((DB_SQL_DIR / "schema.sql").read_text())
    conn.executescript((DB_SQL_DIR / "seed.sql").read_text())
    return conn
