import sqlite3
import tempfile
import unittest
from pathlib import Path

import backfill_magic_lotr_art_series as backfill


class MagicArtSeriesBackfillTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript((Path(__file__).resolve().parents[1] / "db" / "schema.sql").read_text())
        conn.executescript((Path(__file__).resolve().parents[1] / "db" / "seed.sql").read_text())
        expansion = conn.execute(
            "INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code) VALUES (3, 5308, 'LOTR Art Series', 'ltr')"
        ).lastrowid
        self.cards = {}
        for key, number, name in (
            ("normal", "ART-1", "Art Series: Normal Test"),
            ("gold", "ART-2", "Art Series: Gold Test"),
            ("image", "ART-3", "Art Series: Image Test"),
            ("ambiguous", "ART-4", "Art Series: Ambiguous Test"),
        ):
            self.cards[key] = conn.execute(
                """INSERT INTO cards
                   (game_id, expansion_id, card_number, name, printing_variant, set_code, language_id)
                   VALUES (3, ?, ?, ?, 'suggested_parallel', 'ltr', 1)""",
                (expansion, number, name),
            ).lastrowid
        self.products = {}
        for index, key in enumerate(self.cards, start=1):
            self.products[key] = conn.execute(
                """INSERT INTO cardmarket_products
                   (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at)
                   VALUES (?, ?, 1, 5308, '2026-01-01', '2026-01-01')""",
                (800000 + index, conn.execute("SELECT name FROM cards WHERE id=?", (self.cards[key],)).fetchone()[0]),
            ).lastrowid
            conn.execute(
                "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (?, ?, 'mapped')",
                (self.products[key], self.cards[key]),
            )
        conn.execute(
            """INSERT INTO card_images
               (card_id, source, source_variant, source_collector_number, language, face_index,
                match_quality, status, last_checked_at)
               VALUES (?, 'cardtrader', NULL, 'A03', 'en', 0, 'exact', 'resolved', '2026-01-01')""",
            (self.cards["image"],),
        )
        conn.execute(
            """INSERT INTO market_price_history
               (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-02', 4.25, '2026-01-02')""",
            (self.products["normal"],),
        )
        self.collection_id = conn.execute(
            """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, purchase_date, status)
               VALUES (?, ?, 1, 3, 2.75, '2025-01-01', 'KEEP')""",
            (self.cards["normal"], self.products["normal"]),
        ).lastrowid
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_promotes_in_place_classifies_variants_and_preserves_related_data(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        before_cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        export = [{
            "id": "bp-gold",
            "version": "Gold-Stamped",
            "card_market_ids": [str(800002)],
            "fixed_properties": {"collector_number": "A02g"},
        }, {
            "id": "bp-normal",
            "version": "Normal",
            "card_market_ids": [str(800001)],
            "fixed_properties": {"collector_number": "A01"},
        }]
        report = backfill.process_database(conn, apply=True, cardtrader_export=export)
        conn.commit()

        self.assertEqual(report.cards_created, 0)
        self.assertEqual(report.normal, 2)
        self.assertEqual(report.gold_stamped, 1)
        self.assertEqual(report.collection_rows_relinked, 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], before_cards)
        normal = conn.execute("SELECT catalog_status, finish, treatment, source_variant FROM cards WHERE id=?", (self.cards["normal"],)).fetchone()
        gold = conn.execute("SELECT catalog_status, finish, treatment, source_variant FROM cards WHERE id=?", (self.cards["gold"],)).fetchone()
        self.assertEqual(tuple(normal), ("active", "nonfoil", "Art Series", "art_series"))
        self.assertEqual(tuple(gold), ("active", "nonfoil", "Art Series Gold-Stamped", "art_series_gold_stamped"))
        self.assertEqual(conn.execute("SELECT catalog_status FROM cards WHERE id=?", (self.cards["ambiguous"],)).fetchone()[0], "legacy")
        self.assertEqual(tuple(conn.execute("SELECT quantity, purchase_price, purchase_date FROM collection_items WHERE id=?", (self.collection_id,)).fetchone()), (3, 2.75, "2025-01-01"))
        self.assertEqual(conn.execute("SELECT trend FROM market_price_history WHERE cardmarket_product_id=?", (self.products["normal"],)).fetchone()[0], 4.25)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings").fetchone()[0], 4)
        conn.close()

    def test_second_run_is_idempotent(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        export = [{
            "id": "bp-normal",
            "version": "Normal",
            "card_market_ids": [str(800001)],
            "fixed_properties": {"collector_number": "A01"},
        }]
        first = backfill.process_database(conn, apply=True, cardtrader_export=export)
        conn.commit()
        second = backfill.process_database(conn, apply=True, cardtrader_export=export)
        conn.commit()
        self.assertEqual(first.cards_promoted, second.cards_promoted)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_images").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings").fetchone()[0], 4)
        conn.close()

    def test_collection_gold_mode_only_reclassifies_owned_art_series(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute(
            """UPDATE cards
               SET catalog_status='active', finish='nonfoil', release_kind='special', art_kind='special',
                   treatment='Art Series', source_variant='art_series', catalog_source='cardmarket'
               WHERE id IN (?, ?, ?)""",
            (self.cards["normal"], self.cards["gold"], self.cards["image"]),
        )
        conn.execute("UPDATE collection_items SET match_status='exact' WHERE id=?", (self.collection_id,))
        conn.execute(
            "UPDATE cards SET treatment='Art Series Gold-Stamped', source_variant='art_series_gold_stamped' WHERE id=?",
            (self.cards["gold"],),
        )
        owned_gold = conn.execute(
            """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, status)
               VALUES (?, ?, 1, 4, 6.5, 'KEEP')""",
            (self.cards["gold"], self.products["gold"]),
        ).lastrowid
        conn.execute("UPDATE collection_items SET match_status='exact' WHERE id=?", (owned_gold,))
        before_cards = conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
        before_mapping_count = conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings").fetchone()[0]
        before_image_count = conn.execute("SELECT COUNT(*) FROM card_images").fetchone()[0]
        before_snapshot_count = conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0]

        report = backfill.process_collection_art_series_gold(conn, apply=True)
        conn.commit()
        self.assertEqual(report.collection_rows, 2)
        self.assertEqual(report.cards_changed, 1)
        self.assertEqual(report.cards_created, 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], before_cards)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings").fetchone()[0], before_mapping_count)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_images").fetchone()[0], before_image_count)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0], before_snapshot_count)
        self.assertEqual(tuple(conn.execute("SELECT quantity, purchase_price FROM collection_items WHERE id=?", (self.collection_id,)).fetchone()), (3, 2.75))
        self.assertEqual(tuple(conn.execute("SELECT quantity, purchase_price FROM collection_items WHERE id=?", (owned_gold,)).fetchone()), (4, 6.5))
        self.assertEqual(tuple(conn.execute("SELECT treatment, source_variant FROM cards WHERE id=?", (self.cards["normal"],)).fetchone()), ("Art Series Gold-Stamped", "art_series_gold_stamped"))
        self.assertEqual(tuple(conn.execute("SELECT treatment, source_variant FROM cards WHERE id=?", (self.cards["gold"],)).fetchone()), ("Art Series Gold-Stamped", "art_series_gold_stamped"))
        self.assertEqual(tuple(conn.execute("SELECT treatment, source_variant FROM cards WHERE id=?", (self.cards["image"],)).fetchone()), ("Art Series", "art_series"))
        self.assertEqual(conn.execute("SELECT catalog_status FROM cards WHERE id=?", (self.cards["ambiguous"],)).fetchone()[0], "legacy")
        second = backfill.process_collection_art_series_gold(conn, apply=True)
        self.assertEqual(second.cards_changed, 0)
        conn.close()


if __name__ == "__main__":
    unittest.main()
