import tempfile
import unittest
from pathlib import Path

from backend.db.init_db import init_db
from backend.scripts.import_curated_magic_catalog import DEFAULT_CSV, import_csv
from .magic_curated import load_targets, resolve, validate_identity


class CuratedMagicImageTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"db.sqlite"
        init_db(self.db); import_csv(self.db,DEFAULT_CSV,True)
        self.treatments={(s,n):t for s,n,t in load_targets(DEFAULT_CSV)}

    def tearDown(self): self.tmp.cleanup()

    def fetcher(self,code,number):
        treatment=self.treatments[(code,number)]
        return ({"id":f"scryfall-{code}-{number}","set":code,"collector_number":number,"lang":"en",
                 "finishes":["foil"],"promo_types":["surgefoil"] if treatment=="surge_foil" else [],
                 "image_uris":{"small":f"https://cards.scryfall.io/small/{code}/{number}.jpg",
                               "large":f"https://cards.scryfall.io/large/{code}/{number}.jpg"}},None)

    def test_exact_set_number_finish_treatment_and_idempotent_store(self):
        first=resolve(self.db,DEFAULT_CSV,True,fetcher=self.fetcher,delay=0)
        self.assertEqual(first.checked,{"hob":85,"hoc":106})
        self.assertEqual(first.exact,{"hob":85,"hoc":106})
        self.assertEqual((len(first.missing),len(first.ambiguous)),(0,0))
        second=resolve(self.db,DEFAULT_CSV,True,fetcher=lambda *_: (_ for _ in ()).throw(AssertionError("unexpected request")),delay=0)
        self.assertEqual(second.no_op,191)
        self.assertEqual(second.requests,0)
        import sqlite3
        conn=sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT count(*) FROM card_images WHERE source='scryfall' AND status='resolved' AND match_quality='exact'").fetchone()[0],191)
        self.assertEqual(conn.execute("SELECT count(*) FROM cards WHERE catalog_source='cardmadness_curated' AND scryfall_id IS NOT NULL").fetchone()[0],191)
        self.assertEqual(conn.execute("""SELECT count(DISTINCT image_url_large) FROM card_images ci JOIN cards c ON c.id=ci.card_id
            WHERE c.set_code='hob' AND c.card_number IN ('229','265')""").fetchone()[0],2)
        conn.close()

    def test_traditional_identity_uses_exact_number_even_if_scryfall_finish_list_is_nonfoil(self):
        record={"set":"hoc","collector_number":"98","lang":"en","finishes":["nonfoil"],"promo_types":[]}
        self.assertIsNone(validate_identity(record,"hoc","098","traditional_foil"))


if __name__=="__main__": unittest.main()
