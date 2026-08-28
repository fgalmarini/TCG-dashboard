import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

import import_magic_lotr_catalog as importer
import migrate_catalog_wishlist as migration


def card(set_code: str, sf_id: str, number: str, finishes: list[str], **extra) -> dict:
    value = {
        "object": "card", "id": sf_id, "oracle_id": f"oracle-{sf_id}",
        "name": "The One Ring" if number == "246" else "Test LOTR Card",
        "set": set_code, "collector_number": number, "rarity": "mythic",
        "lang": "en", "games": ["paper"], "digital": False,
        "oversized": False, "layout": "normal", "finishes": finishes,
        "promo_types": [], "frame_effects": [], "border_color": "black",
        "image_uris": {"small": f"https://img.test/{sf_id}/small.jpg", "large": f"https://img.test/{sf_id}/large.jpg", "normal": f"https://img.test/{sf_id}/normal.jpg"},
    }
    value.update(extra)
    return value


class CatalogImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        conn = sqlite3.connect(self.db_path)
        conn.executescript((Path(__file__).parent.parent / "db/schema.sql").read_text())
        conn.executescript((Path(__file__).parent.parent / "db/seed.sql").read_text())
        conn.commit()
        conn.close()
        self.fixture = Path(self.tmp.name) / "fixture.json"
        self.fixture.write_text(json.dumps({
            "ltr": [{"object": "list", "data": [
                card("ltr", "sf-ring", "246", ["nonfoil", "foil"], frame_effects=["showcase"]),
                card("ltr", "sf-digital", "A-246", ["nonfoil"], digital=True, games=["arena"], promo_types=["rebalanced"]),
                card("ltr", "sf-token", "T1", ["nonfoil"], layout="token"),
            ]}],
            "ltc": [{"object": "list", "data": [
                card("ltc", "sf-realms", "348", ["foil"], border_color="borderless"),
            ]}],
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def test_fixture_filters_and_expands_real_finishes(self):
        report = importer.import_catalog(self.db_path, fixture=self.fixture, apply=True)
        self.assertEqual(report.by_set["ltr"].rejected_non_physical, 2)
        self.assertEqual(report.by_set["ltr"].inserted, 2)
        self.assertEqual(report.by_set["ltc"].inserted, 1)
        conn = sqlite3.connect(self.db_path)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 3)
        self.assertEqual(
            {row[0] for row in conn.execute("SELECT finish FROM cards")},
            {"nonfoil", "foil"},
        )
        self.assertEqual(conn.execute("SELECT treatment FROM cards WHERE scryfall_id='sf-realms'").fetchone()[0], "Realms & Relics")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_images").fetchone()[0], 3)
        conn.close()

    def test_rerun_is_idempotent_and_treatment_is_not_identity(self):
        importer.import_catalog(self.db_path, fixture=self.fixture, apply=True)
        first = sqlite3.connect(self.db_path)
        ids = {row[0] for row in first.execute("SELECT id FROM cards ORDER BY id")}
        first.close()
        changed = json.loads(self.fixture.read_text())
        changed["ltr"][0]["data"][0]["frame_effects"] = []
        self.fixture.write_text(json.dumps(changed))
        report = importer.import_catalog(self.db_path, fixture=self.fixture, apply=True)
        conn = sqlite3.connect(self.db_path)
        self.assertEqual(ids, {row[0] for row in conn.execute("SELECT id FROM cards ORDER BY id")})
        self.assertEqual(conn.execute("SELECT treatment FROM cards WHERE scryfall_id='sf-ring' AND finish='nonfoil'").fetchone()[0], None)
        self.assertEqual(report.by_set["ltr"].inserted, 0)
        conn.close()


class MigrationTest(unittest.TestCase):
    def test_legacy_migration_preserves_child_references_and_renames_wishlist(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = Path(tmp.name) / "legacy.db"
            conn = sqlite3.connect(db)
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript((Path(__file__).parent.parent / "db/schema.sql").read_text())
            conn.executescript((Path(__file__).parent.parent / "db/seed.sql").read_text())
            conn.execute("DROP TABLE cards")
            conn.execute("DROP TABLE wishlist_items")
            # The fresh schema is only used to create the non-card dependencies;
            # replace these two tables with their actual legacy shapes.
            conn.execute("""CREATE TABLE cards (
                id INTEGER PRIMARY KEY, game_id INTEGER NOT NULL, expansion_id INTEGER NOT NULL,
                card_number TEXT, name TEXT NOT NULL, printing_variant TEXT NOT NULL,
                variant_label TEXT, cardmarket_id_metacard INTEGER, image_url TEXT,
                image_source TEXT, data_source TEXT, scryfall_raw TEXT,
                UNIQUE(expansion_id, card_number, printing_variant)
            )""")
            conn.execute("""CREATE TABLE want_list_items (
                id INTEGER PRIMARY KEY, card_id INTEGER REFERENCES cards(id), language_id INTEGER,
                condition TEXT, grade_min REAL, target_price REAL, max_price REAL,
                priority TEXT NOT NULL, notes TEXT
            )""")
            conn.execute("INSERT INTO expansions (id,game_id,cardmarket_id_expansion,set_code) VALUES (1,3,5285,'ltr')")
            conn.execute("INSERT INTO cards VALUES (7,3,1,'246','The One Ring','normal',NULL,NULL,NULL,NULL,'scryfall', '{\"id\":\"legacy-sf\"}')")
            conn.execute("INSERT INTO cardmarket_products (id,cardmarket_id_product,raw_name,cardmarket_id_category,cardmarket_id_expansion,date_added,last_seen_at) VALUES (1,1,'ring',1,5285,'x','x')")
            conn.execute("INSERT INTO collection_items (id,card_id,cardmarket_product_id,status) VALUES (4,7,1,'KEEP')")
            conn.execute("INSERT INTO want_list_items (id,card_id,priority) VALUES (5,7,'HIGH')")
            conn.commit(); conn.close()
            report = migration.run(db, apply=True)
            self.assertTrue(report.cards_rebuilt)
            conn = sqlite3.connect(db)
            self.assertEqual(conn.execute("SELECT card_id FROM collection_items WHERE id=4").fetchone()[0], 7)
            self.assertEqual(conn.execute("SELECT priority FROM wishlist_items WHERE id=5").fetchone()[0], "high")
            self.assertEqual(conn.execute("SELECT scryfall_id FROM cards WHERE id=7").fetchone()[0], "legacy-sf")
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            conn.close()
        finally:
            tmp.cleanup()

    def test_existing_wishlist_upgrade_preserves_rows_and_is_idempotent(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            db = Path(tmp.name) / "existing.db"
            conn = sqlite3.connect(db)
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript((Path(__file__).parent.parent / "db/schema.sql").read_text())
            conn.executescript((Path(__file__).parent.parent / "db/seed.sql").read_text())
            conn.execute("DROP TABLE wishlist_items")
            conn.execute("""CREATE TABLE wishlist_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, card_id INTEGER NOT NULL,
                quantity_wanted INTEGER NOT NULL DEFAULT 1, priority TEXT NOT NULL,
                max_price REAL, currency TEXT, notes TEXT,
                status TEXT NOT NULL DEFAULT 'wanted', created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL, language_id INTEGER, condition TEXT,
                grade_min REAL, target_price REAL
            )""")
            conn.execute("INSERT INTO expansions (id,game_id,cardmarket_id_expansion,set_code) VALUES (1,3,5285,'ltr')")
            conn.execute("INSERT INTO cards (id,game_id,expansion_id,name,printing_variant) VALUES (7,3,1,'Test','normal')")
            conn.execute(
                """INSERT INTO wishlist_items
                   (id,card_id,quantity_wanted,priority,max_price,target_price,currency,notes,status,created_at,updated_at)
                   VALUES (5,7,2,'high',10,8,'USD','keep','wanted','created','updated')"""
            )
            conn.commit(); conn.close()

            report = migration.run(db, apply=True)
            self.assertTrue(report.wishlist_rebuilt)
            conn = sqlite3.connect(db)
            row = conn.execute(
                "SELECT id,card_id,quantity_wanted,priority,target_price,max_price,status,acquired_at,removed_at FROM wishlist_items"
            ).fetchone()
            self.assertEqual(row, (5, 7, 2, "high", 8, 10, "wanted", None, None))
            self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            conn.close()

            second = migration.run(db, apply=True)
            self.assertFalse(second.wishlist_rebuilt)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
