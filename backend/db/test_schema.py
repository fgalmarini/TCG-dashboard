"""Tests de schema (Fase 3). Corren sobre una DB en memoria, no tocan tcg_dashboard.db."""

import sqlite3
import unittest
from pathlib import Path

SCHEMA_SQL = (Path(__file__).parent / "schema.sql").read_text()
SEED_SQL = (Path(__file__).parent / "seed.sql").read_text()

EXPECTED_TABLES = {
    "games",
    "languages",
    "cardmarket_categories",
    "expansions",
    "cards",
    "cardmarket_products",
    "cardmarket_product_mappings",
    "market_price_history",
    "card_images",
    "collection_items",
    "wishlist_items",
}


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA_SQL)
        self.conn.executescript(SEED_SQL)

    def tearDown(self):
        self.conn.close()

    def test_all_tables_exist(self):
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        table_names = {r[0] for r in rows}
        self.assertTrue(EXPECTED_TABLES.issubset(table_names))

    def test_cards_have_legacy_and_catalog_identity_indexes(self):
        indexes = self.conn.execute("PRAGMA index_list(cards)").fetchall()
        names = {idx[1] for idx in indexes if idx[2] == 1}
        self.assertIn("idx_cards_legacy_identity", names)
        self.assertIn("idx_cards_catalog_identity", names)
        self.assertIn("idx_cards_scryfall_finish_identity", names)

    def test_catalog_identity_allows_real_finish_variants(self):
        self.conn.execute(
            "INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code) "
            "VALUES (3, 5285, 'LTR', 'ltr')"
        )
        expansion_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        for finish in ("nonfoil", "foil"):
            self.conn.execute(
                """INSERT INTO cards
                   (game_id, expansion_id, card_number, name, printing_variant,
                    set_code, normalized_name, finish, language_id)
                   VALUES (3, ?, '1', 'The One Ring', 'normal', 'ltr',
                           'the one ring', ?, 1)""",
                (expansion_id, finish),
            )
        self.conn.commit()

    def test_catalog_identity_rejects_duplicate_same_finish(self):
        self.conn.execute(
            "INSERT INTO expansions (game_id, cardmarket_id_expansion, name, set_code) "
            "VALUES (3, 5285, 'LTR', 'ltr')"
        )
        expansion_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant,
                set_code, normalized_name, finish, language_id)
               VALUES (3, ?, '1', 'The One Ring', 'normal', 'ltr',
                       'the one ring', 'foil', 1)""",
            (expansion_id,),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                """INSERT INTO cards
                   (game_id, expansion_id, card_number, name, printing_variant,
                    set_code, normalized_name, finish, language_id)
                   VALUES (3, ?, '1', 'The One Ring', 'normal', 'ltr',
                           'the one ring', 'foil', 1)""",
                (expansion_id,),
            )

    def test_market_price_history_unique_index(self):
        indexes = self.conn.execute("PRAGMA index_list(market_price_history)").fetchall()
        found = False
        for idx in indexes:
            if idx[2] == 1:
                cols = [r[2] for r in self.conn.execute(f"PRAGMA index_info({idx[1]})")]
                if set(cols) == {"cardmarket_product_id", "observed_at"}:
                    found = True
        self.assertTrue(found, "falta UNIQUE(cardmarket_product_id, observed_at) en market_price_history")

    def test_seed_data(self):
        games = {r[0] for r in self.conn.execute("SELECT code FROM games")}
        self.assertEqual(games, {"pokemon", "one_piece", "magic"})
        languages = {r[0] for r in self.conn.execute("SELECT code FROM languages")}
        self.assertIn("en", languages)

    def test_foreign_keys_enforced_end_to_end(self):
        self.conn.execute(
            "INSERT INTO expansions (game_id, cardmarket_id_expansion, name) VALUES (3, 5285, 'LTR')"
        )
        self.conn.execute(
            """INSERT INTO cards (game_id, expansion_id, name, printing_variant)
               VALUES (3, 1, 'The One Ring', 'normal')"""
        )
        self.conn.execute(
            """INSERT INTO cardmarket_products
               (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
                date_added, last_seen_at)
               VALUES (123456, 'The One Ring', 1, 5285, '2026-01-01', '2026-01-01')"""
        )
        self.conn.execute(
            """INSERT INTO collection_items (card_id, cardmarket_product_id, status)
               VALUES (1, 1, 'KEEP')"""
        )
        self.conn.commit()

        violations = self.conn.execute("PRAGMA foreign_key_check").fetchall()
        self.assertEqual(violations, [])

        row = self.conn.execute("SELECT language_id FROM collection_items WHERE id = 1").fetchone()
        self.assertEqual(row[0], 1)  # default -> languages.id = 1 ('en')

    def test_games_code_check_constraint(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO games (code, name) VALUES ('yugioh', 'Yu-Gi-Oh!')")

    def test_card_images_accepts_cardtrader_and_keeps_unique_key(self):
        self.conn.execute(
            "INSERT INTO expansions (game_id, cardmarket_id_expansion, name) "
            "VALUES (3, 9999, 'CardTrader fixture')"
        )
        expansion_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            "INSERT INTO cards (game_id, expansion_id, name, printing_variant) "
            "VALUES (3, ?, 'CardTrader fixture', 'normal')",
            (expansion_id,),
        )
        card_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            "INSERT INTO card_images (card_id, source, source_card_id, source_variant, "
            "source_collector_number, language, face_index, image_url_large, "
            "match_quality, status, last_checked_at) "
            "VALUES (?, 'cardtrader', '123', 'Gold-Stamped', 'A01g', 'en', 0, "
            "'https://cardtrader.com/image.jpg', 'exact', 'resolved', '2026-01-01T00:00:00Z')",
            (card_id,),
        )
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute(
                "INSERT INTO card_images (card_id, source, source_card_id, language, face_index, "
                "image_url_large, match_quality, status, last_checked_at) VALUES "
                "(?, 'cardtrader', '456', 'en', 0, 'https://cardtrader.com/other.jpg', "
                "'exact', 'resolved', '2026-01-01T00:00:00Z')",
                (card_id,),
            )


if __name__ == "__main__":
    unittest.main()
