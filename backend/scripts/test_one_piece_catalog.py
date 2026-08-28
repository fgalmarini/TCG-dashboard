import datetime as dt
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

import import_one_piece_catalog as importer
import migrate_multi_tcg


class OnePieceCatalogImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = self.root / "catalog.db"
        conn = sqlite3.connect(self.db)
        db_dir = Path(__file__).parent.parent / "db"
        conn.executescript((db_dir / "schema.sql").read_text())
        conn.executescript((db_dir / "seed.sql").read_text())
        conn.execute("INSERT INTO cardmarket_categories (game_id,cardmarket_id_category,category_name,is_single) VALUES (2,1621,'One Piece Single',1)")
        conn.execute("INSERT INTO expansions (game_id,cardmarket_id_expansion,name) VALUES (2,5229,'OP01')")
        expansion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO cards (game_id,expansion_id,card_number,name,printing_variant,language_id) VALUES (2,?,'OP01-001','Roronoa Zoro','normal',1)", (expansion_id,))
        legacy_card = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO cardmarket_products (cardmarket_id_product,raw_name,cardmarket_id_category,cardmarket_id_expansion,date_added,last_seen_at) VALUES (690001,'Roronoa Zoro (OP01-001)',1621,5229,'2026-01-01','2026-01-01')")
        product_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO cardmarket_product_mappings (cardmarket_product_id,card_id,status) VALUES (?,?,'mapped')", (product_id, legacy_card))
        conn.commit(); conn.close()

        self.fixture = self.root / "fixture.json"
        self.fixture.write_text(json.dumps({"expansions": [{
            "id": 3332, "game_id": 15, "code": "op01", "name": "OP-01: Romance Dawn",
            "blueprints": [{
                "id": 244001, "name": "Roronoa Zoro", "version": "Alternate Art | Reprint",
                "game_id": 15, "category_id": 192, "expansion_id": 3332,
                "card_market_ids": [690001],
                "image_url": "https://cardtrader.com/zoro.jpg",
                "fixed_properties": {"collector_number": "OP01-001", "onepiece_rarity": "Leader"},
                "editable_properties": [{"name": "onepiece_language", "default_value": "en", "possible_values": ["en", "jp"]}],
            }],
        }]}))
        self.registry = self.root / "registry.json"
        self.registry.write_text(json.dumps({"checked_at": "2026-08-27", "overrides": {}}))

    def tearDown(self):
        self.tmp.cleanup()

    def test_import_is_idempotent_and_keeps_language_specific_internal_ids(self):
        first = importer.import_catalog(
            self.db, fixture=self.fixture, registry_path=self.registry, apply=True,
            as_of=dt.date(2026, 8, 27), observed_at="2026-08-27T00:00:00+00:00",
        )
        self.assertEqual(first.en_printings, 1)
        self.assertEqual(first.jp_printings, 1)
        conn = sqlite3.connect(self.db)
        rows = conn.execute(
            """SELECT c.id,l.code,c.release_kind,c.art_kind
                 FROM cards c JOIN languages l ON l.id=c.language_id
                WHERE c.catalog_status='active' ORDER BY l.code"""
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertNotEqual(rows[0][0], rows[1][0])
        self.assertEqual({row[2] for row in rows}, {"reprint"})
        self.assertEqual({row[3] for row in rows}, {"alternate_art"})
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_images WHERE status='resolved'").fetchone()[0], 1)
        ids_before = {row[0] for row in rows}
        conn.close()

        importer.import_catalog(
            self.db, fixture=self.fixture, registry_path=self.registry, apply=True,
            as_of=dt.date(2026, 8, 27), observed_at="2026-08-27T00:00:00+00:00",
        )
        conn = sqlite3.connect(self.db)
        ids_after = {row[0] for row in conn.execute("SELECT id FROM cards WHERE catalog_status='active'")}
        self.assertEqual(ids_before, ids_after)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_external_ids WHERE source='cardtrader_blueprint'").fetchone()[0], 2)
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()

    def test_additive_migration_is_idempotent(self):
        first = migrate_multi_tcg.run(self.db, apply=True)
        second = migrate_multi_tcg.run(self.db, apply=True)
        self.assertGreaterEqual(first.magic_canonical_cards, 0)
        self.assertEqual(second.columns_added, 0)

    def test_commercial_identity_collision_is_preserved_as_ambiguous(self):
        payload = json.loads(self.fixture.read_text())
        duplicate = dict(payload["expansions"][0]["blueprints"][0])
        duplicate["id"] = 244002
        duplicate["card_market_ids"] = []
        payload["expansions"][0]["blueprints"].append(duplicate)
        self.fixture.write_text(json.dumps(payload))

        report = importer.import_catalog(
            self.db, fixture=self.fixture, registry_path=self.registry, apply=True,
            as_of=dt.date(2026, 8, 27), observed_at="2026-08-27T00:00:00+00:00",
        )
        self.assertEqual(report.commercial_identity_conflict_groups, 2)
        self.assertEqual(report.ambiguous_commercial_printings, 4)
        conn = sqlite3.connect(self.db)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM cards WHERE catalog_status='ambiguous'").fetchone()[0],
            4,
        )
        self.assertEqual(
            conn.execute("SELECT COUNT(DISTINCT id) FROM cards WHERE catalog_status='ambiguous'").fetchone()[0],
            4,
        )
        conn.close()


if __name__ == "__main__":
    unittest.main()
