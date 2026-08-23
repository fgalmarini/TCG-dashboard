"""Corre el pipeline completo contra fixtures locales (sin red), sobre un archivo temporal
(no :memory:) para poder correrlo 2 veces y verificar idempotencia -- contrato Fase 4, verificacion #4."""

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_import
from downloader import DownloadResult

FIXTURES_DIR = Path(__file__).parent / "fixtures"
DB_SQL_DIR = Path(__file__).resolve().parent.parent / "db"


def _result_for(path: Path) -> DownloadResult:
    return DownloadResult(str(path), str(path), path, True, path.stat().st_size, None)


def _fake_download_results() -> dict:
    return {
        "magic:products": _result_for(FIXTURES_DIR / "sample_products_magic.json"),
        "magic:price_guide": _result_for(FIXTURES_DIR / "sample_price_guide_magic.json"),
        "one_piece:products": _result_for(FIXTURES_DIR / "sample_products_one_piece.json"),
        "one_piece:price_guide": _result_for(FIXTURES_DIR / "sample_price_guide_one_piece.json"),
        # pokemon: SCOPE="skip", nunca se lee, pero download_all igual las trae.
        "pokemon:products": _result_for(FIXTURES_DIR / "sample_products_magic.json"),
        "pokemon:price_guide": _result_for(FIXTURES_DIR / "sample_price_guide_magic.json"),
    }


class RunImportIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((DB_SQL_DIR / "schema.sql").read_text())
        conn.executescript((DB_SQL_DIR / "seed.sql").read_text())
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _run(self):
        with patch("run_import.downloader.download_all", return_value=_fake_download_results()), \
             patch("run_import.db.connect", side_effect=self._connect):
            return run_import.run_import()

    def _query_one(self, sql: str):
        conn = self._connect()
        try:
            return conn.execute(sql).fetchone()[0]
        finally:
            conn.close()

    def test_first_run_loads_expected_counts(self):
        report = self._run()

        self.assertEqual(report.products_seen["magic"], {"total": 5, "singles": 4, "in_scope": 3})
        self.assertEqual(report.products_seen["one_piece"], {"total": 4, "singles": 3, "in_scope": 3})

        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cardmarket_products WHERE cardmarket_id_expansion = 5285"), 3)
        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cardmarket_products"), 6)  # 3 magic in-scope + 3 one_piece singles
        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cards"), 6)

        self.assertIn(("magic", 5285), report.new_expansions)
        self.assertIn(("one_piece", 1), report.new_expansions)

        self.assertEqual(sorted(report.one_piece_unparsed_names), ["DON!!", "Monkey.D.Luffy"])
        self.assertEqual(report.date_sentinel_substitutions.get("one_piece"), 1)

        # sin colecciones/want-list todavia (Fase 5 no existe) -> 0 filas de histórico.
        self.assertEqual(self._query_one("SELECT COUNT(*) FROM market_price_history"), 0)

        # Pokemon nunca se carga a la DB.
        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cardmarket_products WHERE cardmarket_id_category = 51"), 0)

    def test_variant_group_classification(self):
        self._run()
        rows = dict(self._query_pairs(
            "SELECT cp.cardmarket_id_product, c.printing_variant "
            "FROM cardmarket_products cp "
            "JOIN cardmarket_product_mappings cpm ON cpm.cardmarket_product_id = cp.id "
            "JOIN cards c ON c.id = cpm.card_id "
            "WHERE cp.cardmarket_id_product IN (1002, 1003)"
        ))
        self.assertEqual(rows[1002], "normal")
        self.assertEqual(rows[1003], "suggested_parallel")

    def _query_pairs(self, sql: str):
        conn = self._connect()
        try:
            return conn.execute(sql).fetchall()
        finally:
            conn.close()

    def test_second_run_is_idempotent(self):
        self._run()
        second_report = self._run()

        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cardmarket_products"), 6)
        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cards"), 6)
        self.assertEqual(self._query_one("SELECT COUNT(*) FROM cardmarket_product_mappings"), 6)
        # ya estaban resueltas de la corrida anterior -> nada nuevo que reportar como expansion.
        self.assertEqual(second_report.new_expansions, [])


if __name__ == "__main__":
    unittest.main()
