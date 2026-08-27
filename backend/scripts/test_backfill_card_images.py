import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.api import test_support
from backend.api.db import connect
from backend.images.cardtrader import CardTraderCatalog
import backfill_card_images


ROOT_CARD = {
    "id": "sf-root",
    "lang": "en",
    "image_uris": {
        "small": "https://cards.scryfall.io/small/front/a/a/root.jpg",
        "large": "https://cards.scryfall.io/large/front/a/a/root.jpg",
    },
}

MULTI_FACE_CARD = {
    "id": "sf-multi",
    "lang": "en",
    "card_faces": [
        {"image_uris": {"small": "https://cards.scryfall.io/small/front/b/b/front.jpg"}},
        {"image_uris": {"large": "https://cards.scryfall.io/large/back/b/b/back.jpg"}},
    ],
}


class BackfillCardImagesTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"
        test_support.make_test_db(self.db_path)
        self.conn = connect(self.db_path)
        self.ids = test_support.insert_fixtures(self.conn)
        self.conn.execute("DELETE FROM card_images")
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        self.tmp_dir.cleanup()

    def test_dry_run_reports_pending_network_without_calling_fetcher(self):
        self.conn.execute(
            "UPDATE cards SET scryfall_raw = ? WHERE id = ?",
            (json.dumps(ROOT_CARD), self.ids["card_a_id"]),
        )
        self.conn.commit()
        calls = []

        def fetcher(_cardmarket_id_product):
            calls.append(_cardmarket_id_product)
            return ROOT_CARD, None

        report, scopes = backfill_card_images.run_backfill(
            self.db_path,
            apply_changes=False,
            allow_network=False,
            fetcher=fetcher,
        )

        self.assertEqual(calls, [])
        self.assertEqual(report.resolved_exact, 1)
        self.assertEqual(report.would_request_network, 1)
        self.assertEqual(report.network_requests, 0)
        self.assertEqual(report.total_canonical_cards, 2)
        self.assertEqual(sum(scope.collection_rows for scope in scopes), 3)

    def test_apply_is_idempotent_and_preserves_collection_tables(self):
        self.conn.execute(
            "UPDATE cards SET scryfall_raw = ? WHERE id = ?",
            (json.dumps(ROOT_CARD), self.ids["card_a_id"]),
        )
        self.conn.execute(
            "UPDATE cards SET scryfall_raw = ? WHERE id = ?",
            (json.dumps(MULTI_FACE_CARD), self.ids["card_b_id"]),
        )
        before_collection_count = self.conn.execute("SELECT COUNT(*) FROM collection_items").fetchone()[0]
        self.conn.commit()

        report1, _ = backfill_card_images.run_backfill(self.db_path, apply_changes=True, allow_network=False)
        report2, _ = backfill_card_images.run_backfill(self.db_path, apply_changes=True, allow_network=False)

        image_rows = self.conn.execute("SELECT COUNT(*) FROM card_images").fetchone()[0]
        after_collection_count = self.conn.execute("SELECT COUNT(*) FROM collection_items").fetchone()[0]
        self.assertEqual(image_rows, 3)
        self.assertEqual(before_collection_count, after_collection_count)
        self.assertEqual(report1.resolved_exact, 2)
        self.assertEqual(report1.multi_face, 1)
        self.assertEqual(report2.existing_exact, 2)
        self.assertEqual(report2.resolved_exact, 0)

    def test_apply_uses_direct_cardmarket_lookup_when_raw_is_missing(self):
        self.conn.execute(
            "UPDATE cards SET scryfall_raw = ? WHERE id = ?",
            (json.dumps(ROOT_CARD), self.ids["card_a_id"]),
        )
        self.conn.commit()
        calls = []

        def fetcher(cardmarket_id_product):
            calls.append(cardmarket_id_product)
            return MULTI_FACE_CARD, None

        report, _ = backfill_card_images.run_backfill(
            self.db_path,
            apply_changes=True,
            allow_network=True,
            fetcher=fetcher,
        )

        self.assertEqual(calls, [1002])
        self.assertEqual(report.network_requests, 1)
        self.assertEqual(report.resolved_from_network, 1)
        rows = self.conn.execute(
            "SELECT face_index FROM card_images WHERE card_id = ? ORDER BY face_index",
            (self.ids["card_b_id"],),
        ).fetchall()
        self.assertEqual([row[0] for row in rows], [0, 1])

    def test_cardtrader_fallback_persists_large_only_and_metadata(self):
        catalog = CardTraderCatalog.from_blueprints([{
            "id": 9001,
            "name": "Art Series: Test",
            "version": "Gold-Stamped",
            "card_market_ids": [1002],
            "image_url": "https://cardtrader.com/uploads/test.jpg",
            "fixed_properties": {"collector_number": "A01g"},
            "editable_properties": [{"name": "mtg_language", "default_value": "en"}],
        }])
        report, _ = backfill_card_images.run_backfill(
            self.db_path,
            apply_changes=True,
            allow_network=False,
            cardtrader_catalog=catalog,
        )
        row = self.conn.execute(
            "SELECT source, source_card_id, source_variant, source_collector_number, "
            "image_url_small, image_url_large FROM card_images WHERE card_id = ?",
            (self.ids["card_b_id"],),
        ).fetchone()
        self.assertEqual(row[0], "cardtrader")
        self.assertEqual(row[1:4], ("9001", "Gold-Stamped", "A01g"))
        self.assertIsNone(row[4])
        self.assertEqual(row[5], "https://cardtrader.com/uploads/test.jpg")
        self.assertEqual(report.cardtrader_exact_candidates, 1)
        self.assertEqual(report.gold_stamped_candidates, 1)

    def test_cardtrader_duplicate_and_missing_are_not_persisted(self):
        catalog = CardTraderCatalog.from_blueprints([
            {
                "id": 9001, "name": "Test A", "version": None, "card_market_ids": [1002],
                "image_url": "https://cardtrader.com/a.jpg", "fixed_properties": {},
            },
            {
                "id": 9002, "name": "Test B", "version": None, "card_market_ids": [1002],
                "image_url": "https://cardtrader.com/b.jpg", "fixed_properties": {},
            },
        ])
        report, _ = backfill_card_images.run_backfill(
            self.db_path, apply_changes=True, allow_network=False, cardtrader_catalog=catalog
        )
        self.assertEqual(len(report.cardtrader_ambiguous), 1)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM card_images WHERE source = 'cardtrader'").fetchone()[0], 0)

    def test_scryfall_exact_has_priority_over_cardtrader(self):
        self.conn.execute(
            "UPDATE cards SET scryfall_raw = ? WHERE id = ?",
            (json.dumps(ROOT_CARD), self.ids["card_a_id"]),
        )
        self.conn.commit()
        catalog = CardTraderCatalog.from_blueprints([{
            "id": 9001, "name": "Test", "version": "Gold-Stamped", "card_market_ids": [1001],
            "image_url": "https://cardtrader.com/should-not-be-used.jpg", "fixed_properties": {},
        }])
        report, _ = backfill_card_images.run_backfill(
            self.db_path, apply_changes=True, allow_network=False, cardtrader_catalog=catalog
        )
        sources = self.conn.execute("SELECT source FROM card_images WHERE card_id = ?", (self.ids["card_a_id"],)).fetchall()
        self.assertEqual([row[0] for row in sources], ["scryfall"])
        self.assertEqual(report.cardtrader_exact_candidates, 0)

    def test_schema_migration_preserves_old_rows_ids_and_indexes(self):
        self.conn.execute("DROP TABLE card_images")
        self.conn.execute(
            """CREATE TABLE card_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id),
                source TEXT NOT NULL CHECK (source IN ('scryfall', 'manual')),
                source_card_id TEXT,
                language TEXT NOT NULL,
                face_index INTEGER NOT NULL CHECK (face_index >= 0),
                image_url_small TEXT,
                image_url_large TEXT,
                match_quality TEXT NOT NULL CHECK (match_quality IN ('exact', 'representative', 'manual')),
                status TEXT NOT NULL CHECK (status IN ('resolved', 'ambiguous', 'missing', 'error')),
                last_checked_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(card_id, source, language, face_index)
            )"""
        )
        self.conn.execute("CREATE INDEX idx_card_images_card_id ON card_images(card_id)")
        self.conn.execute(
            "INSERT INTO card_images (id, card_id, source, source_card_id, language, face_index, "
            "image_url_small, image_url_large, match_quality, status, last_checked_at) "
            "VALUES (77, ?, 'scryfall', 'old', 'en', 0, 'small', 'large', 'exact', 'resolved', 'now')",
            (self.ids["card_a_id"],),
        )
        self.conn.commit()
        backfill_card_images.ensure_schema(self.conn)
        self.conn.commit()
        row = self.conn.execute("SELECT id, card_id, source_card_id, image_url_large, source_variant FROM card_images").fetchone()
        self.assertEqual(tuple(row), (77, self.ids["card_a_id"], "old", "large", None))
        self.assertIn("idx_card_images_card_id", [row[1] for row in self.conn.execute("PRAGMA index_list(card_images)")])
        self.assertEqual(self.conn.execute("PRAGMA integrity_check").fetchone()[0], "ok")
        self.assertEqual(self.conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_schema_without_source_check_adds_columns_without_rebuild(self):
        self.conn.execute("DROP TABLE card_images")
        self.conn.execute(
            """CREATE TABLE card_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_id INTEGER NOT NULL REFERENCES cards(id),
                source TEXT NOT NULL,
                source_card_id TEXT,
                language TEXT NOT NULL,
                face_index INTEGER NOT NULL,
                image_url_small TEXT,
                image_url_large TEXT,
                match_quality TEXT NOT NULL,
                status TEXT NOT NULL,
                last_checked_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(card_id, source, language, face_index)
            )"""
        )
        self.conn.execute(
            "INSERT INTO card_images (card_id, source, source_card_id, language, face_index, "
            "image_url_large, match_quality, status, last_checked_at) "
            "VALUES (?, 'cardtrader', '9001', 'en', 0, 'large', 'exact', 'resolved', 'now')",
            (self.ids["card_a_id"],),
        )
        self.conn.commit()
        before_rootpage = self.conn.execute(
            "SELECT rootpage FROM sqlite_master WHERE type='table' AND name='card_images'"
        ).fetchone()[0]
        backfill_card_images.ensure_schema(self.conn)
        self.conn.commit()
        after_rootpage = self.conn.execute(
            "SELECT rootpage FROM sqlite_master WHERE type='table' AND name='card_images'"
        ).fetchone()[0]
        self.assertEqual(before_rootpage, after_rootpage)
        self.assertEqual(
            tuple(self.conn.execute("SELECT source, source_card_id, image_url_large FROM card_images").fetchone()),
            ("cardtrader", "9001", "large"),
        )
        columns = {row[1] for row in self.conn.execute("PRAGMA table_info(card_images)")}
        self.assertTrue({"source_variant", "source_collector_number"}.issubset(columns))


if __name__ == "__main__":
    unittest.main()
