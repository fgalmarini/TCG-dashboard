import hashlib
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import import_pokemon_151 as importer


ROOT = Path(__file__).resolve().parents[2]
DISCOVERY = ROOT / "reports/pokemon_151/identity_discovery"


class Pokemon151CatalogImportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "catalog.db"
        conn = sqlite3.connect(self.db)
        conn.executescript((ROOT / "backend/db/schema.sql").read_text())
        conn.executescript((ROOT / "backend/db/seed.sql").read_text())
        conn.commit()
        conn.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_does_not_write_and_apply_is_exact_and_idempotent(self):
        before = hashlib.sha256(self.db.read_bytes()).hexdigest()
        dry = importer.run(self.db, DISCOVERY, Path(self.tmp.name) / "reports", Path(self.tmp.name) / "backups", False)
        self.assertEqual(dry["official_rows_valid"], 207)
        self.assertEqual(dry["new_canonical_rows"], 207)
        self.assertEqual(dry["new_physical_rows"], 362)
        self.assertEqual(hashlib.sha256(self.db.read_bytes()).hexdigest(), before)

        importer.run(self.db, DISCOVERY, Path(self.tmp.name) / "reports", Path(self.tmp.name) / "backups", True)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM canonical_cards WHERE game_id=1").fetchone()[0], 207)
        self.assertEqual(conn.execute("SELECT COUNT(DISTINCT card_number) FROM cards WHERE game_id=1 AND set_code='mew'").fetchone()[0], 207)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards WHERE game_id=1 AND set_code='mew'").fetchone()[0], 362)
        self.assertEqual(dict(conn.execute("SELECT finish,COUNT(*) FROM cards WHERE game_id=1 AND set_code='mew' GROUP BY finish").fetchall()), {"normal": 128, "holo": 81, "reverse_holo": 153})
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM card_images WHERE source='tcgdex'").fetchone()[0], 362)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cardmarket_product_mappings WHERE card_id IN (SELECT id FROM cards WHERE game_id=1)").fetchone()[0], 0)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM printing_price_resolutions WHERE card_id IN (SELECT id FROM cards WHERE game_id=1)").fetchone()[0], 0)
        self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(), [])
        conn.close()

        second = importer.run(self.db, DISCOVERY, Path(self.tmp.name) / "reports2", Path(self.tmp.name) / "backups2", False)
        self.assertEqual(second["new_canonical_rows"], 0)
        self.assertEqual(second["new_physical_rows"], 0)
        self.assertEqual(second["new_image_rows"], 0)

    def test_same_name_numbered_identities_and_images_stay_distinct(self):
        importer.run(self.db, DISCOVERY, Path(self.tmp.name) / "reports", Path(self.tmp.name) / "backups", True)
        conn = sqlite3.connect(self.db)
        rows = conn.execute("SELECT canonical_number,id FROM canonical_cards WHERE game_id=1 AND name='Mew ex' ORDER BY canonical_number").fetchall()
        self.assertEqual([row[0] for row in rows], ["151", "193", "205"])
        self.assertEqual(len({row[1] for row in rows}), 3)
        image_sources = conn.execute("SELECT DISTINCT c.card_number,ci.source_card_id FROM cards c JOIN card_images ci ON ci.card_id=c.id WHERE c.game_id=1 AND c.card_number IN ('006','183','199') ORDER BY c.card_number,ci.source_card_id").fetchall()
        self.assertEqual({row[1] for row in image_sources}, {"sv03.5-006", "sv03.5-183", "sv03.5-199"})
        metadata = json.loads(conn.execute("SELECT metadata FROM canonical_cards WHERE game_id=1 AND canonical_number='001'").fetchone()[0])
        self.assertEqual(metadata["pokemon"]["artist"], "Yuu Nishida")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards WHERE game_id=1 AND treatment IS NOT NULL").fetchone()[0], 0)
        conn.close()

    def test_schema_extension_preserves_existing_magic_rows_and_accepts_pokemon_vocabulary(self):
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO expansions (game_id,cardmarket_id_expansion,name,set_code) VALUES (3,900001,'Test','tst')")
        expansion = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO cards (game_id,expansion_id,card_number,name,printing_variant,finish,language_id) VALUES (3,?,'1','Existing','normal','foil',1)", (expansion,))
        conn.commit(); conn.close()
        importer.run(self.db, DISCOVERY, Path(self.tmp.name) / "reports", Path(self.tmp.name) / "backups", True)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards WHERE game_id=3 AND name='Existing'").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards WHERE game_id=1 AND finish='reverse_holo'").fetchone()[0], 153)
        conn.close()


if __name__ == "__main__":
    unittest.main()
