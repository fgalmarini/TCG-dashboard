import sqlite3
import tempfile
import unittest
from pathlib import Path

from backend.db.init_db import init_db
from backend.scripts.import_curated_magic_catalog import DEFAULT_CSV, SNAPSHOT, import_csv


class CuratedMagicCatalogTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"test.db"
        init_db(self.db)

    def tearDown(self): self.tmp.cleanup()

    def test_curated_counts_prices_and_repeat_run(self):
        first=import_csv(self.db,DEFAULT_CSV,True)
        self.assertEqual(first["logical"],{"HOB":50,"HOC":66})
        self.assertEqual(first["printings"],191)
        self.assertEqual(first["observations_inserted"],86)
        conn=sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT count(*) FROM canonical_cards WHERE identity_key LIKE 'curated:%'").fetchone()[0],116)
        self.assertEqual(conn.execute("SELECT count(*) FROM cards WHERE lower(set_code) IN ('hob','hoc') AND finish='foil'").fetchone()[0],191)
        self.assertEqual(conn.execute("SELECT count(*) FROM cards WHERE lower(set_code) IN ('hob','hoc') AND finish='nonfoil'").fetchone()[0],0)
        self.assertEqual(conn.execute("SELECT count(*) FROM cards WHERE lower(set_code) IN ('hob','hoc') AND language_id<>(SELECT id FROM languages WHERE code='en')").fetchone()[0],0)
        self.assertEqual(conn.execute("SELECT count(*) FROM cards WHERE lower(set_code) IN ('hob','hoc') AND treatment='traditional_foil'").fetchone()[0],116)
        self.assertEqual(conn.execute("SELECT count(*) FROM cards WHERE lower(set_code) IN ('hob','hoc') AND treatment='surge_foil'").fetchone()[0],75)
        self.assertEqual(conn.execute("""SELECT count(*) FROM cards s JOIN cards t ON s.canonical_card_id=t.canonical_card_id
            WHERE s.treatment='surge_foil' AND t.treatment='traditional_foil'
              AND s.canonical_card_id IS NOT NULL AND lower(s.set_code) IN ('hob','hoc')""").fetchone()[0],75)
        self.assertEqual(conn.execute("SELECT count(DISTINCT card_id) FROM market_price_observations WHERE snapshot_key=?",(SNAPSHOT,)).fetchone()[0],61)
        self.assertEqual(conn.execute("SELECT count(*) FROM market_price_observations WHERE snapshot_key=?",(SNAPSHOT,)).fetchone()[0],86)
        smaug=conn.execute("""SELECT o.metric,o.value FROM market_price_observations o JOIN cards c ON c.id=o.card_id
            WHERE c.set_code='hob' AND c.card_number='265' AND o.snapshot_key=?""",(SNAPSHOT,)).fetchall()
        self.assertEqual(dict(smaug),{"low":24999.99,"avg30":10100.0})
        second=import_csv(self.db,DEFAULT_CSV,True)
        self.assertEqual(second["observations_inserted"],0)
        self.assertEqual(second["observations_no_op"],86)
        self.assertEqual(second["conflicts"],[])
        conn.close()


if __name__ == "__main__": unittest.main()
