import csv
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import import_pokemon_151
import resolve_pokemon_151_cardmarket
from apply_pokemon_151_cardmarket_manual_review import ReviewGateError, run


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"
PRODUCTS = Path("/Users/facundogalmarini/Desktop/products_singles_6 (1).json")
PRICES = Path("/Users/facundogalmarini/Desktop/price_guide_6 (1).json")


class Pokemon151ManualReviewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "catalog.db"
        conn = sqlite3.connect(self.db)
        conn.executescript((ROOT / "backend/db/schema.sql").read_text())
        conn.executescript((ROOT / "backend/db/seed.sql").read_text())
        conn.commit(); conn.close()
        import_pokemon_151.run(self.db, DISCOVERY, self.root / "catalog-reports", self.root / "catalog-backups", True)
        resolve_pokemon_151_cardmarket.run(self.db, PRODUCTS, PRICES, DISCOVERY, self.root / "mapping-reports", self.root / "mapping-backups", True)
        self.output = self.root / "manual-resolution"
        self.review = self.output / "03_manual_review.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def prepare_review(self):
        run(self.db, self.review, self.output, self.root / "backups", False)

    def edit_review(self, product_id, **changes):
        with self.review.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle)); fields = rows[0].keys()
        for row in rows:
            if int(row["idProduct"]) == product_id:
                row.update({key: str(value) for key, value in changes.items()})
        with self.review.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    def test_workspace_is_exactly_73_rows_and_defaults_to_pending(self):
        result = run(self.db, self.review, self.output, self.root / "backups", False)
        with self.review.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 73)
        self.assertEqual({row["approved"] for row in rows}, {"false"})
        self.assertEqual(result["approved_valid_rows"], 0)

    def test_tampered_immutable_field_aborts(self):
        self.prepare_review()
        self.edit_review(719442, product_name="tampered")
        with self.assertRaisesRegex(ReviewGateError, "REVIEW_FILE_TAMPERED"):
            run(self.db, self.review, self.output, self.root / "backups", False)

    def test_duplicate_product_row_is_rejected(self):
        self.prepare_review()
        with self.review.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle)); fields = rows[0].keys()
        rows.append(dict(rows[0]))
        with self.review.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        with self.assertRaisesRegex(ReviewGateError, "REVIEW_FILE_TAMPERED"):
            run(self.db, self.review, self.output, self.root / "backups", False)

    def test_number_outside_presented_candidates_is_not_valid(self):
        self.prepare_review()
        self.edit_review(719442, approved="true", approved_collector_number="207")
        result = run(self.db, self.review, self.output, self.root / "backups", False)
        self.assertEqual(result["approved_valid_rows"], 0)
        rows = list(csv.DictReader((self.output / "04_apply_dry_run.csv").open(encoding="utf-8")))
        row = next(item for item in rows if item["idProduct"] == "719442")
        self.assertEqual(row["validation_status"], "APPROVED_NUMBER_NOT_IN_CANDIDATES")

    def test_zero_approval_apply_is_byte_identical_and_creates_no_backup(self):
        self.prepare_review()
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        backup = self.root / "backups"
        result = run(self.db, self.review, self.output, backup, True)
        self.assertEqual(result["approved_valid_rows"], 0)
        self.assertEqual(result["db_mutation"], 0)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)
        self.assertFalse(backup.exists())

    def test_valid_approval_preserves_existing_finish_fields_and_is_idempotent(self):
        conn = sqlite3.connect(self.db); conn.row_factory = sqlite3.Row
        canonical_id = conn.execute("SELECT id FROM canonical_cards WHERE identity_key='pokemon:mew:001'").fetchone()[0]
        card_id = conn.execute("SELECT id FROM cards WHERE canonical_card_id=? AND finish='normal' LIMIT 1", (canonical_id,)).fetchone()[0]
        product_id = conn.execute("SELECT id FROM cardmarket_products WHERE cardmarket_id_product=719442").fetchone()[0]
        conn.execute("""INSERT INTO cardmarket_product_printing_scopes
            (cardmarket_product_id, canonical_card_id, card_id, finish_scope, compatible_finishes,
             numbered_identity_status, finish_mapping_status, mapping_status, mapping_confidence,
             mapping_method, evidence, provenance, pricing_eligible)
            VALUES (?, ?, ?, 'single', '[\"normal\"]', 'AMBIGUOUS', 'AMBIGUOUS', 'AMBIGUOUS',
                    'LOW', 'test', 'before', 'before', 0)""", (product_id, canonical_id, card_id))
        conn.commit(); conn.close()
        self.prepare_review(); self.edit_review(719442, approved="true", approved_collector_number="001", review_notes="approved by test")
        protected_before = self.table_hashes(["market_price_history", "printing_price_resolutions", "market_price_observations", "cardmarket_product_metric_mappings"])
        result = run(self.db, self.review, self.output, self.root / "backups", True)
        self.assertEqual(result["approved_valid_rows"], 1)
        conn = sqlite3.connect(self.db); conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM cardmarket_product_printing_scopes WHERE cardmarket_product_id=(SELECT id FROM cardmarket_products WHERE cardmarket_id_product=719442)").fetchone()
        self.assertEqual(row["mapping_status"], "EXACT")
        self.assertEqual(row["numbered_identity_status"], "EXACT")
        self.assertEqual(row["mapping_method"], "manual_review")
        self.assertEqual(row["card_id"], card_id)
        self.assertEqual(row["finish_scope"], "single")
        self.assertEqual(row["compatible_finishes"], '["normal"]')
        self.assertEqual(row["pricing_eligible"], 0)
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()
        self.assertEqual(protected_before, self.table_hashes(["market_price_history", "printing_price_resolutions", "market_price_observations", "cardmarket_product_metric_mappings"]))

        second_before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        second = run(self.db, self.review, self.output / "second", self.root / "second-backups", True)
        self.assertEqual(second["approved_valid_rows"], 0)
        self.assertEqual(second["db_mutation"], 0)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), second_before)

    def table_hashes(self, tables):
        conn = sqlite3.connect(self.db); digest = hashlib.sha256()
        for table in tables:
            rows = conn.execute(f'SELECT * FROM "{table}" ORDER BY rowid').fetchall()
            digest.update(table.encode()); digest.update(json.dumps(rows, default=list).encode())
        conn.close(); return digest.hexdigest()


if __name__ == "__main__":
    unittest.main()
