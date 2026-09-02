import csv
import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import import_pokemon_151
import resolve_pokemon_151_cardmarket
from pokemon_151_test_sources import make_cardmarket_sources
from apply_pokemon_151_cardmarket_manual_review import (
    ReviewGateError,
    cardmarket_candidate_search_url,
    cardmarket_product_slug,
    cardmarket_product_versions_url,
    deterministic_collector_number,
    load_price_guide,
    normalize_tcgdex_url,
    price_based_recommendation,
    price_metrics_for,
    price_tier,
    recommendation_for,
    run,
)


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"


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
        self.products_fixture, self.prices_fixture = make_cardmarket_sources(self.root, DISCOVERY)
        resolve_pokemon_151_cardmarket.run(self.db, self.products_fixture, self.prices_fixture, DISCOVERY, self.root / "mapping-reports", self.root / "mapping-backups", True)
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

    def test_tcgdex_urls_are_browser_ready_and_preserve_existing_extensions(self):
        base = "https://assets.tcgdex.net/en/sv/sv03.5/001"
        self.assertEqual(normalize_tcgdex_url(base), base + "/high.webp")
        self.assertEqual(normalize_tcgdex_url(base, thumbnail=True), base + "/low.webp")
        for extension in ("webp", "png", "jpg"):
            url = base + "." + extension
            self.assertEqual(normalize_tcgdex_url(url), url)
        external = "https://example.test/card/001"
        self.assertEqual(normalize_tcgdex_url(external), external)

    def test_cardmarket_slug_and_review_urls_are_stable(self):
        product_name = "Bulbasaur [Leech Seed | 151]"
        self.assertEqual(cardmarket_product_slug(product_name), "Bulbasaur-Leech-Seed-151")
        self.assertEqual(
            cardmarket_product_versions_url(product_name),
            "https://www.cardmarket.com/en/Pokemon/Cards/Bulbasaur-Leech-Seed-151/Versions",
        )
        self.assertEqual(
            cardmarket_candidate_search_url("Bulbasaur", "001"),
            "https://www.cardmarket.com/en/Pokemon/Products/Search?searchString=Bulbasaur+MEW001",
        )

    def test_review_html_and_recommendation_report_are_generated(self):
        result = run(self.db, self.review, self.output, self.root / "backups", False)
        self.assertTrue((self.output / "review.html").exists())
        self.assertTrue((self.output / "auto_recommendations.csv").exists())
        html = (self.output / "review.html").read_text(encoding="utf-8")
        self.assertIn("idProduct", html)
        self.assertIn("idMetacard", html)
        self.assertIn("Bulbasaur", html)
        self.assertIn("Yuu Nishida", html)
        self.assertIn("/001/low.webp", html)
        self.assertIn("Open Cardmarket versions", html)
        self.assertIn("Open Cardmarket candidate", html)
        self.assertIn("/Cards/Bulbasaur-Leech-Seed-151/Versions", html)
        self.assertIn("searchString=Bulbasaur+MEW001", html)
        self.assertIn("Cardmarket Low", html)
        self.assertIn("Trend-Holo", html)
        self.assertIn("€0.02", html)
        self.assertIn("€13.50", html)
        self.assertIn("Avg30", html)
        recommendations = list(csv.DictReader((self.output / "auto_recommendations.csv").open(encoding="utf-8")))
        self.assertEqual(len(recommendations), 73)
        self.assertEqual(
            {"cardmarket_low", "cardmarket_trend", "cardmarket_avg7", "price_tier", "recommendation_reason"},
            set(recommendations[0]).intersection({"cardmarket_low", "cardmarket_trend", "cardmarket_avg7", "price_tier", "recommendation_reason"}),
        )
        self.assertEqual(sum(result["recommendation_counts"].values()), 73)
        self.assertEqual(result["recommendation_counts"]["AUTO_EXACT"], 0)
        self.assertGreater(result["recommendation_counts"]["RECOMMENDED"], 0)

    def test_auto_exact_requires_explicit_numbered_evidence(self):
        candidates = ["001", "166"]
        name_only = {
            "matched_collector_number": "001", "mapping_evidence": "name_signature=bulbasaur",
            "notes": "idMetacard retained as grouping evidence", "mapping_method": "retained_ambiguous_candidate_set",
        }
        self.assertEqual(deterministic_collector_number(name_only, candidates), "")
        explicit = {
            **name_only,
            "mapping_evidence": "direct_external_id_match; exact_collector_number=001",
        }
        self.assertEqual(deterministic_collector_number(explicit, candidates), "001")
        numbered_exact = {**name_only, "numbered_identity_status": "EXACT"}
        self.assertEqual(deterministic_collector_number(numbered_exact, candidates), "001")
        candidate_rows = [{"number": "001", "name": "Bulbasaur", "attacks": []}, {"number": "166", "name": "Bulbasaur", "attacks": []}]
        self.assertEqual(recommendation_for(name_only, candidate_rows, "Bulbasaur" )["status"], "NEEDS_REVIEW")
        self.assertEqual(recommendation_for(name_only, candidate_rows, "Bulbasaur", {"cardmarket_low": 0.02})["status"], "RECOMMENDED")
        self.assertNotEqual(recommendation_for(name_only, candidate_rows, "Bulbasaur", {"cardmarket_low": 0.02})["status"], "AUTO_EXACT")

    def test_price_guide_metrics_and_tiers_are_review_only(self):
        guide = load_price_guide()
        metrics = price_metrics_for(guide, 719442)
        self.assertEqual(metrics["cardmarket_low"], 0.02)
        self.assertEqual(metrics["cardmarket_trend"], 0.24)
        self.assertEqual(metrics["cardmarket_avg7"], 0.07)
        self.assertEqual(metrics["cardmarket_low_holo"], 0.1)
        self.assertEqual(price_tier(metrics["cardmarket_low"]), "LOW")
        self.assertEqual(price_tier(13.5), "HIGH")
        self.assertEqual(price_tier(None), "UNKNOWN")

    def test_price_recommendations_are_suggestions_and_flag_contradictions(self):
        candidates = [
            {"number": "001", "name": "Bulbasaur", "attacks": []},
            {"number": "166", "name": "Bulbasaur", "attacks": []},
        ]
        low = price_based_recommendation({"cardmarket_low": 0.02}, candidates)
        high = price_based_recommendation({"cardmarket_low": 13.5}, candidates)
        contradictory = price_based_recommendation({"cardmarket_low": 13.5}, [candidates[0]])
        self.assertEqual((low["status"], low["recommended_candidate"]), ("RECOMMENDED", "001"))
        self.assertEqual((high["status"], high["recommended_candidate"]), ("RECOMMENDED", "166"))
        self.assertEqual(contradictory["status"], "NEEDS_REVIEW")

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

    def test_dry_run_does_not_mutate_db_or_prices(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        prices_before = self.table_hashes(["market_price_history", "printing_price_resolutions", "market_price_observations"])
        result = run(self.db, self.review, self.output, self.root / "backups", False)
        self.assertEqual(result["db_mutation"], 0)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)
        self.assertEqual(prices_before, self.table_hashes(["market_price_history", "printing_price_resolutions", "market_price_observations"]))

    def test_valid_approval_inserts_canonical_only_scope_without_finish_or_prices(self):
        self.prepare_review()
        self.edit_review(719444, approved="true", approved_collector_number="002")
        protected_before = self.table_hashes([
            "market_price_history", "printing_price_resolutions", "market_price_observations",
            "cardmarket_product_metric_mappings",
        ])

        result = run(self.db, self.review, self.output, self.root / "backups", True)

        self.assertEqual(result["approved_valid_rows"], 1)
        conn = sqlite3.connect(self.db); conn.row_factory = sqlite3.Row
        row = conn.execute("""SELECT s.*
              FROM cardmarket_product_printing_scopes s
              JOIN cardmarket_products p ON p.id=s.cardmarket_product_id
             WHERE p.cardmarket_id_product=719444""").fetchone()
        self.assertIsNotNone(row)
        self.assertIsNone(row["card_id"])
        self.assertEqual(row["finish_scope"], "unknown")
        self.assertEqual(row["compatible_finishes"], "[]")
        self.assertEqual(row["numbered_identity_status"], "EXACT")
        self.assertEqual(row["finish_mapping_status"], "UNKNOWN")
        self.assertEqual(row["mapping_status"], "EXACT")
        self.assertEqual(row["mapping_confidence"], "MANUAL")
        self.assertEqual(row["mapping_method"], "manual_review")
        self.assertEqual(row["pricing_eligible"], 0)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()
        self.assertEqual(protected_before, self.table_hashes([
            "market_price_history", "printing_price_resolutions", "market_price_observations",
            "cardmarket_product_metric_mappings",
        ]))

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
        scope_before = self.table_hashes(["games", "cards", "collection_items", "wishlist_items"])
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
        self.assertEqual(scope_before, self.table_hashes(["games", "cards", "collection_items", "wishlist_items"]))

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
