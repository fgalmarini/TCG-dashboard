import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audit_pricing


class AuditPricingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "audit.db"
        self.source = self.root / "sources"
        (self.source / "one-piece").mkdir(parents=True)
        (self.source / "magic").mkdir(parents=True)
        conn = sqlite3.connect(self.db)
        conn.executescript((Path(__file__).resolve().parents[1] / "db/schema.sql").read_text())
        conn.executescript((Path(__file__).resolve().parents[1] / "db/seed.sql").read_text())
        conn.execute("INSERT INTO cardmarket_categories (game_id, cardmarket_id_category, category_name, is_single) VALUES (2, 1800, 'One Piece Single', 1)")
        conn.execute("INSERT INTO cardmarket_categories (game_id, cardmarket_id_category, category_name, is_single) VALUES (3, 1900, 'Magic Single', 1)")
        conn.execute("INSERT INTO expansions (id, game_id, cardmarket_id_expansion, name, set_code) VALUES (1, 2, 200, 'OP01', 'op01')")
        conn.execute("INSERT INTO expansions (id, game_id, cardmarket_id_expansion, name, set_code) VALUES (2, 3, 300, 'LTR', 'ltr')")
        conn.execute("INSERT INTO cards (id, game_id, expansion_id, card_number, name, printing_variant, set_code, language_id, catalog_status) VALUES (1, 2, 1, 'OP01-001', 'Luffy', 'normal', 'op01', 1, 'active')")
        conn.execute("INSERT INTO cards (id, game_id, expansion_id, card_number, name, printing_variant, set_code, language_id, finish, catalog_status, scryfall_raw, scryfall_id) VALUES (2, 3, 2, '1', 'Ring', 'normal', 'ltr', 1, 'foil', 'active', ?, 'scry-1')", (json.dumps({"cardmarket_id": 201, "finishes": ["nonfoil", "foil"]}),))
        conn.execute("INSERT INTO cardmarket_products (id, cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at) VALUES (1, 101, 'Luffy (OP01-001)', 1800, 200, '2026-01-01', '2026-01-01')")
        conn.execute("INSERT INTO cardmarket_products (id, cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at) VALUES (2, 201, 'Ring', 1900, 300, '2026-01-01', '2026-01-01')")
        conn.execute("INSERT INTO cardmarket_products (id, cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at) VALUES (3, 202, 'Ring', 1900, 999, '2026-01-01', '2026-01-01')")
        conn.execute("INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (1, 1, 'mapped')")
        conn.execute("INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (3, 2, 'mapped')")
        conn.execute("INSERT INTO printing_external_ids (card_id, source, external_id, language_id, language_scope, metadata) VALUES (1, 'cardmarket_product', '101', 1, 'exact', '{\"allowed_languages\":[\"en\"]}')")
        conn.execute("INSERT INTO market_price_history (cardmarket_product_id, observed_at, low, avg, trend, avg1, avg7, avg30, trend_alt, imported_at) VALUES (1, '2026-08-29T00:00:00+00:00', 8, 9, 10, 9, 10, 11, 0, '2026-08-29T00:00:00+00:00')")
        conn.execute("INSERT INTO market_price_history (cardmarket_product_id, observed_at, low, avg, trend, avg1, avg7, avg30, trend_alt, imported_at) VALUES (2, '2026-08-29T00:00:00+00:00', 2, 3, 3, 3, 3, 3, 5, '2026-08-29T00:00:00+00:00')")
        conn.execute("INSERT INTO printing_price_resolutions (card_id, language_id, resolved_at, current_price, currency, source, resolution_method, external_id, price_confidence) VALUES (1, 1, '2026-08-29T00:00:00+00:00', 9, 'EUR', 'cardmarket', 'cardmarket_exact_language', '101', 'high')")
        conn.execute("INSERT INTO collection_items (card_id, cardmarket_product_id, language_id, quantity, status) VALUES (1, 1, 1, 2, 'KEEP')")
        conn.commit()
        conn.close()
        self._write_sources()

    def tearDown(self):
        self.tmp.cleanup()

    def _write_sources(self):
        payloads = {
            "one-piece/products_singles_18.json": {"version": 1, "createdAt": "2026-08-29T00:00:00+00:00", "products": [{"idProduct": 101, "name": "Luffy (OP01-001)", "idCategory": 1800, "idExpansion": 200, "idMetacard": 1}]},
            "one-piece/price_guide_18.json": {"version": 1, "createdAt": "2026-08-29T00:00:00+00:00", "priceGuides": [{"idProduct": 101, "low": 8, "avg": 9, "trend": 10, "avg1": 9, "avg7": 10, "avg30": 11}]},
            "magic/products_singles_1.json": {"version": 1, "createdAt": "2026-08-29T00:00:00+00:00", "products": [{"idProduct": 201, "name": "Ring", "idCategory": 1900, "idExpansion": 300, "idMetacard": 2}]},
            "magic/price_guide_1.json": {"version": 1, "createdAt": "2026-08-29T00:00:00+00:00", "priceGuides": [{"idProduct": 201, "low": 2, "avg": 3, "trend": 3, "avg1": 3, "avg7": 3, "avg30": 3, "low-foil": 4, "avg-foil": 5, "trend-foil": 5, "avg1-foil": 5, "avg7-foil": 5, "avg30-foil": 5}]},
        }
        for relative, payload in payloads.items():
            path = self.source / relative
            path.write_text(json.dumps(payload), encoding="utf-8")

    def _context(self, game):
        conn = audit_pricing.connect_read_only(self.db)
        cards = audit_pricing.load_cards(conn, (game,))
        external = audit_pricing.load_external_ids(conn)
        mappings = audit_pricing.load_mappings(conn)
        resolutions, histories = audit_pricing.load_current_prices(conn)
        names = audit_pricing.load_expansion_names(conn)
        snapshots, _ = audit_pricing.load_snapshots(self.source, (game,), conn, "2026-08-29T00:00:00+00:00")
        products, _ = audit_pricing.build_product_indexes(snapshots[game]["products"], game)
        prices = {int(row["idProduct"]): dict(row) for row in snapshots[game]["price_guide"].records}
        return conn, cards[0], products, prices, external, mappings, resolutions, histories, names

    def test_exact_id_and_price_comparison(self):
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "one_piece", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "EXACT")
        self.assertEqual(row["resolved_cardmarket_id"], 101)
        self.assertAlmostEqual(row["price_difference"], 1)
        self.assertAlmostEqual(row["low_vs_trend_difference"], -2)
        self.assertEqual(row["price_severity"], "OK")
        conn.close()

    def test_mixed_language_is_ambiguous(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE printing_external_ids SET language_scope='mixed', metadata=? WHERE card_id=1", (json.dumps({"allowed_languages": ["en", "jp"]}),))
        conn.commit()
        conn.close()
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "one_piece", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "AMBIGUOUS")
        conn.close()

    def test_magic_wrong_mapping_is_mismatch(self):
        ctx = self._context("magic")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "magic", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "MISMATCH")
        self.assertTrue(row["identity_mismatch"])
        conn.close()

    def test_magic_foil_uses_foil_metric_and_flags_dashboard_metric(self):
        conn = sqlite3.connect(self.db)
        conn.execute("DELETE FROM cardmarket_product_mappings WHERE card_id=2")
        conn.execute("INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (2, 2, 'mapped')")
        conn.commit()
        conn.close()
        ctx = self._context("magic")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "magic", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "EXACT")
        self.assertEqual(row["cardmarket_metric_used"], "Foil Low")
        self.assertFalse(row["metric_mismatch"])
        conn.close()

    def test_source_validation_rejects_missing_snapshot(self):
        missing = self.root / "missing"
        missing.mkdir()
        conn = audit_pricing.connect_read_only(self.db)
        with self.assertRaises(audit_pricing.AuditError):
            audit_pricing.load_snapshots(missing, ("one_piece",), conn, "2026-08-29T00:00:00+00:00")
        conn.close()

    def test_full_audit_is_read_only_and_deterministic(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        first = self.root / "report-1"
        second = self.root / "report-2"
        audit_pricing.audit(db_path=self.db, source_dir=self.source, output_dir=first, games=("one_piece", "magic"), display_currency="EUR", now="2026-08-29T00:00:00+00:00")
        audit_pricing.audit(db_path=self.db, source_dir=self.source, output_dir=second, games=("one_piece", "magic"), display_currency="EUR", now="2026-08-29T00:00:00+00:00")
        after = hashlib.sha256(self.db.read_bytes()).hexdigest()
        self.assertEqual(before, after)
        self.assertEqual((first / "one_piece_full.csv").read_bytes(), (second / "one_piece_full.csv").read_bytes())
        manifest = json.loads((first / "source_manifest.json").read_text())
        self.assertEqual(manifest["database"]["query_only"], 1)
        self.assertTrue(manifest["database"]["unchanged"])
        self.assertEqual(manifest["safe_to_run_update_prices_apply"], "NO")

    def test_severity_boundaries_trend_null_and_zero(self):
        self.assertEqual(audit_pricing.price_severity(0.15), "OK")
        self.assertEqual(audit_pricing.price_severity(0.30), "REVIEW")
        self.assertEqual(audit_pricing.price_severity(0.75), "HIGH")
        self.assertEqual(audit_pricing.price_severity(0.750001), "CRITICAL")
        self.assertEqual(audit_pricing.price_severity(None), "NO_COMPARISON")
        self.assertEqual(audit_pricing.price_severity(0.01, True), "CRITICAL")

    def test_low_is_pricing_control_and_low_vs_trend_is_informational(self):
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "one_piece", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["cardmarket_metric_used"], "Low")
        self.assertEqual(row["price_severity"], "OK")
        self.assertEqual(row["low_difference"], 1.0)
        self.assertEqual(row["low_vs_trend_difference"], -2.0)
        conn.close()

    def test_currency_mismatch_does_not_compare(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE printing_price_resolutions SET currency='USD' WHERE card_id=1")
        conn.commit()
        conn.close()
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "one_piece", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertTrue(row["currency_mismatch"])
        self.assertIsNone(row["percentage_difference"])
        self.assertEqual(row["primary_cause"], "currency_mismatch")
        conn.close()

    def test_current_null_resolution_wins_over_older_price(self):
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE printing_price_resolutions SET is_current=0 WHERE card_id=1")
        conn.execute("INSERT INTO printing_price_resolutions (card_id, language_id, resolved_at, current_price, currency, source, resolution_method, match_status, is_current) VALUES (1, 1, '2026-08-30T00:00:00Z', NULL, 'EUR', 'cardmarket', 'no_exact_language_price', 'AMBIGUOUS', 1)")
        conn.commit(); conn.close()
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "one_piece", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertIsNone(row["current_price"])
        self.assertEqual(row["match_status"], "EXACT")
        conn.close()
    def test_wrong_language_version_and_expansion_are_explicit(self):
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        wrong_language = deepcopy(external)
        wrong_language[1][0]["language_scope"] = "exact"
        wrong_language[1][0]["metadata"] = {"allowed_languages": ["jp"]}
        identity = audit_pricing.resolve_identity(card, "one_piece", products, wrong_language, mappings, names)
        self.assertEqual(identity.status, "MISMATCH")
        self.assertIn("wrong_language", identity.evidence["mismatch_reasons"])
        version_card = deepcopy(card)
        version_card["variant_label"] = "V.2"
        product = deepcopy(products[101])
        product["version"] = "V.3"
        matches, reasons = audit_pricing._product_matches_card(version_card, product, "one_piece", names)
        self.assertFalse(matches)
        self.assertIn("wrong_version", reasons)
        matches, reasons = audit_pricing._product_matches_card(card, {**products[101], "idExpansion": 999}, "one_piece", {999: "Different set"})
        self.assertFalse(matches)
        self.assertIn("wrong_expansion", reasons)
        conn.close()

    def test_ambiguous_and_missing_are_fail_safe(self):
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        second = {**products[101], "idProduct": 102}
        ambiguous_external = deepcopy(external)
        ambiguous_external[1].append({"source": "cardmarket_product", "external_id": "102", "language_id": 1, "language_scope": "mixed", "metadata": {}})
        identity = audit_pricing.resolve_identity(card, "one_piece", {101: products[101], 102: second}, ambiguous_external, mappings, names)
        self.assertEqual(identity.status, "AMBIGUOUS")
        missing_card = deepcopy(card)
        missing_card["id"] = 99
        identity = audit_pricing.resolve_identity(missing_card, "one_piece", {}, {}, {}, names)
        self.assertEqual(identity.status, "MISSING")
        self.assertEqual(identity.primary_cause, "missing_cardmarket_id")
        conn.close()

    def test_special_magic_treatments_are_not_inferred(self):
        ctx = self._context("magic")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        mappings[2] = [{"card_id": 2, "status": "mapped", "local_product_id": 2, "cardmarket_id_product": 201}]
        special = deepcopy(card)
        special["treatment"] = "Surge Foil"
        raw = json.loads(special["scryfall_raw"])
        raw["promo_types"] = ["surgefoil"]
        special["scryfall_raw"] = json.dumps(raw)
        row = audit_pricing.audit_card(special, "magic", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "AMBIGUOUS")
        etched = deepcopy(card)
        etched["finish"] = "etched"
        etched["treatment"] = "Etched"
        raw = json.loads(etched["scryfall_raw"])
        raw["finishes"] = ["etched"]
        etched["scryfall_raw"] = json.dumps(raw)
        row = audit_pricing.audit_card(etched, "magic", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "AMBIGUOUS")
        art = deepcopy(card)
        art["treatment"] = "Art Series Gold-Stamped"
        row = audit_pricing.audit_card(art, "magic", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "AMBIGUOUS")
        conn.close()

    def test_nonfoil_and_unpriced_trend_handling(self):
        ctx = self._context("magic")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        mappings[2] = [{"card_id": 2, "status": "mapped", "local_product_id": 2, "cardmarket_id_product": 201}]
        nonfoil = deepcopy(card)
        nonfoil["finish"] = "nonfoil"
        row = audit_pricing.audit_card(nonfoil, "magic", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
        self.assertEqual(row["match_status"], "EXACT")
        self.assertEqual(row["cardmarket_metric_used"], "Low")
        for trend in (None, 0):
            row = audit_pricing.audit_card(nonfoil, "magic", products, {201: {"trend": trend}}, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "EUR")
            self.assertEqual(row["match_status"], "UNPRICED")
            self.assertIsNone(row["percentage_difference"])
            self.assertIsNone(row["ratio"])
        conn.close()

    def test_collection_resolved_low_aggregate_multiplies_quantity(self):
        rows = [
            {
                "collection_item_id": 1, "collection_quantity": 2,
                "match_status": "EXACT", "resolved_cardmarket_id": 101,
                "cardmarket_metric_used": "Low", "low": 10.0,
                "current_price": 10.0, "currency_mismatch": False,
            },
            {
                "collection_item_id": 2, "collection_quantity": 3,
                "match_status": "EXACT", "resolved_cardmarket_id": 102,
                "cardmarket_metric_used": "Low", "low": 1.0,
                "current_price": 1.0, "currency_mismatch": False,
            },
        ]

        audit_pricing.refresh_collection_contributions(rows)
        summary = audit_pricing.collection_summary(rows, [{"quantity": 2}, {"quantity": 3}])

        self.assertEqual([row["collection_cardmarket_contribution"] for row in rows], [20.0, 3.0])
        self.assertEqual(summary["resolved_low_total"], 23.0)

    def test_collection_unpriced_does_not_fallback_from_foil_low_to_base_low(self):
        rows = [
            {
                "collection_item_id": 65, "collection_quantity": 1,
                "match_status": "EXACT", "resolved_cardmarket_id": 738134,
                "cardmarket_metric_used": "Foil Low", "low": 0.05,
                "low_alt": None, "current_price": None,
                "currency_mismatch": False,
            },
            {
                "collection_item_id": 66, "collection_quantity": 1,
                "match_status": "UNPRICED", "resolved_cardmarket_id": 738135,
                "cardmarket_metric_used": "Low", "low": 99.0,
                "current_price": None, "currency_mismatch": False,
            },
        ]

        audit_pricing.refresh_collection_contributions(rows)
        summary = audit_pricing.collection_summary(rows, [{"quantity": 1}, {"quantity": 1}])

        self.assertIsNone(rows[0]["collection_cardmarket_contribution"])
        self.assertTrue(audit_pricing.collection_unpriced(rows[0]))
        self.assertTrue(audit_pricing.collection_unpriced(rows[1]))
        self.assertEqual(summary["resolved_low_total"], 0.0)

    def test_display_currency_and_blueprint_collision_diagnostics(self):
        ctx = self._context("one_piece")
        conn, card, products, prices, external, mappings, resolutions, histories, names = ctx
        row = audit_pricing.audit_card(card, "one_piece", products, prices, external, mappings, resolutions, histories, names, {}, "2026-08-29T00:00:00+00:00", "USD")
        self.assertTrue(row["currency_mismatch"])
        diagnostics = audit_pricing.blueprint_diagnostics(conn)
        self.assertEqual(diagnostics, {})
        conn.close()

    def test_incompatible_snapshot_is_rejected(self):
        bad = self.root / "bad-sources"
        (bad / "one-piece").mkdir(parents=True)
        (bad / "one-piece/products_singles_18.json").write_text(json.dumps({"createdAt": "2026-08-29T00:00:00Z", "products": [{"idProduct": 1, "idCategory": 1800, "idExpansion": 200}]}))
        (bad / "one-piece/price_guide_18.json").write_text(json.dumps({"createdAt": "2026-08-29T00:00:00Z", "priceGuides": [{"idProduct": 1, "trend": 1}]}))
        conn = audit_pricing.connect_read_only(self.db)
        with self.assertRaises(audit_pricing.AuditError):
            audit_pricing.load_snapshots(bad, ("one_piece",), conn, "2026-08-29T00:00:00+00:00")
        conn.close()

    def test_read_only_connection_checks_and_rejects_writes(self):
        conn = audit_pricing.connect_read_only(self.db)
        self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 1)
        self.assertEqual(conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertIsNone(conn.execute("PRAGMA foreign_key_check").fetchone())
        with self.assertRaises(sqlite3.OperationalError):
            conn.execute("CREATE TABLE forbidden_audit_write (id INTEGER)")
        conn.close()


if __name__ == "__main__":
    unittest.main()
