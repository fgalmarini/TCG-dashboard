"""Test de robustez del loop principal (security review, hallazgo ID-001):
una excepcion no prevista en apply_scryfall_data no debe propagarse fuera de
run_backfill -- se reporta en report.unexpected_errors y el loop sigue, en vez de
cortar antes del conn.commit() final y perder las actualizaciones ya aplicadas."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scryfall_backfill as sb

DB_SQL_DIR = Path(__file__).resolve().parent.parent / "db"


class RunBackfillUnexpectedErrorTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"

        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((DB_SQL_DIR / "schema.sql").read_text())
        conn.executescript((DB_SQL_DIR / "seed.sql").read_text())

        # game_id 3 = magic (seed.sql). Un producto en scope, ya mapeado a una card.
        conn.execute("INSERT INTO expansions (game_id, cardmarket_id_expansion) VALUES (3, 5285)")
        expansion_id = conn.execute(
            "SELECT id FROM expansions WHERE cardmarket_id_expansion = 5285"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO cards (game_id, expansion_id, name, printing_variant) VALUES (3, ?, 'Placeholder', 'normal')",
            (expansion_id,),
        )
        card_id = conn.execute("SELECT id FROM cards WHERE name = 'Placeholder'").fetchone()[0]
        conn.execute(
            """INSERT INTO cardmarket_products
                 (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
                  date_added, last_seen_at)
               VALUES (111, 'Placeholder', 1, 5285, '2026-01-01', '2026-01-01')"""
        )
        product_id = conn.execute(
            "SELECT id FROM cardmarket_products WHERE cardmarket_id_product = 111"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (?, ?, 'mapped')",
            (product_id, card_id),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_unexpected_exception_is_reported_not_propagated(self):
        fake_data = {"set": "ltr", "set_name": "Test Set", "name": "Placeholder"}

        with patch("scryfall_backfill.fetch_scryfall_card", return_value=(fake_data, None)), \
             patch("scryfall_backfill.apply_scryfall_data", side_effect=TypeError("unexpected JSON shape")):
            report = sb.run_backfill(self.db_path)

        # No propago: run_backfill devolvio un reporte normal, no lanzo.
        self.assertEqual(report.resolved_ok, 0)
        self.assertEqual(len(report.unexpected_errors), 1)
        id_product, reason = report.unexpected_errors[0]
        self.assertEqual(id_product, 111)
        self.assertIn("TypeError", reason)
        self.assertIn("unexpected JSON shape", reason)

        # El commit final se ejecuto igual (la excepcion no corto el loop antes de
        # tiempo) -- la conexion se puede reabrir sin problemas.
        conn = sqlite3.connect(self.db_path)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 1)
        conn.close()

    def test_unexpected_exception_does_not_block_other_products_in_same_run(self):
        """Un segundo producto en scope, sin excepcion, se procesa igual aunque el
        primero haya disparado un error no previsto."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO cardmarket_products
                 (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
                  date_added, last_seen_at)
               VALUES (222, 'Placeholder 2', 1, 5285, '2026-01-01', '2026-01-01')"""
        )
        expansion_id = conn.execute(
            "SELECT id FROM expansions WHERE cardmarket_id_expansion = 5285"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO cards (game_id, expansion_id, name, printing_variant) VALUES (3, ?, 'Placeholder 2', 'normal')",
            (expansion_id,),
        )
        card_id = conn.execute("SELECT id FROM cards WHERE name = 'Placeholder 2'").fetchone()[0]
        product_id = conn.execute(
            "SELECT id FROM cardmarket_products WHERE cardmarket_id_product = 222"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (?, ?, 'mapped')",
            (product_id, card_id),
        )
        conn.commit()
        conn.close()

        fake_data = {"set": "ltr", "set_name": "Test Set", "name": "Placeholder"}
        real_apply = sb.apply_scryfall_data

        def flaky_apply(conn, card_id, expansion_id, data, report):
            if data.get("name") == "Placeholder" and card_id == 1:
                raise TypeError("unexpected JSON shape")
            return real_apply(conn, card_id, expansion_id, data, report)

        with patch("scryfall_backfill.fetch_scryfall_card", return_value=(fake_data, None)), \
             patch("scryfall_backfill.apply_scryfall_data", side_effect=flaky_apply):
            report = sb.run_backfill(self.db_path)

        self.assertEqual(len(report.unexpected_errors), 1)
        self.assertEqual(report.resolved_ok, 1)


if __name__ == "__main__":
    unittest.main()
