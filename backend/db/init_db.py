"""Create (or update) the TCG Dashboard SQLite database from schema.sql + seed.sql.

Usage:
    python3 backend/db/init_db.py [path/to/db]
"""

import sqlite3
import sys
from pathlib import Path

DB_DIR = Path(__file__).parent
DEFAULT_DB_PATH = DB_DIR / "tcg_dashboard.db"


def init_db(db_path: Path) -> None:
    schema_sql = (DB_DIR / "schema.sql").read_text()
    seed_sql = (DB_DIR / "seed.sql").read_text()

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(schema_sql)
        conn.executescript(seed_sql)
        conn.commit()

        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        ).fetchall()
        games = conn.execute("SELECT code FROM games ORDER BY id").fetchall()
        languages = conn.execute("SELECT code FROM languages ORDER BY id").fetchall()
    finally:
        conn.close()

    print(f"DB creada/actualizada en: {db_path}")
    print(f"Tablas ({len(tables)}): {', '.join(t[0] for t in tables)}")
    print(f"games seed: {', '.join(g[0] for g in games)}")
    print(f"languages seed: {', '.join(l[0] for l in languages)}")


if __name__ == "__main__":
    db_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    init_db(db_path)
