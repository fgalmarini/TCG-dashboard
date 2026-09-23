import unittest
from fastapi.testclient import TestClient

from . import test_support
from .db import connect, get_db
from .main import app


class EventWishlistApiTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path
        self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"test.db"
        test_support.make_test_db(self.db)
        conn=connect(self.db); self.ids=test_support.insert_fixtures(conn)
        conn.execute("UPDATE cards SET catalog_status='active' WHERE id IN (?,?)",(self.ids['card_a_id'],self.ids['card_b_id']))
        conn.commit(); conn.close()
        def override():
            db=connect(self.db)
            try: yield db
            finally: db.close()
        app.dependency_overrides[get_db]=override; self.client=TestClient(app)

    def tearDown(self): app.dependency_overrides.clear(); self.tmp.cleanup()

    def test_only_linked_items_show_and_wishlist_status_remains_authoritative(self):
        a=self.client.post('/api/wishlist',json={'card_id':self.ids['card_a_id']}).json()
        b=self.client.post('/api/wishlist',json={'card_id':self.ids['card_b_id']}).json()
        path='/api/events/cardmadness-2026/wishlist'
        self.assertEqual(self.client.post(path,json={'wishlist_item_id':a['id']}).status_code,204)
        self.assertEqual(self.client.post(path,json={'wishlist_item_id':a['id']}).status_code,204)
        event_item=self.client.get(path).json()['items'][0]
        self.assertEqual([event_item['wishlist_item']['id']],[a['id']])
        self.assertEqual(event_item['wishlist_item']['image']['source'],'scryfall')
        catalog=self.client.get('/api/catalog',params={'search':'Test Card A'}).json()
        self.assertEqual(catalog['items'][0]['image']['source'],'scryfall')
        self.client.post(f"/api/wishlist/{a['id']}/mark-acquired")
        self.assertEqual(self.client.get(path).json()['items'][0]['wishlist_item']['status'],'acquired')
        self.assertEqual(self.client.delete(f"{path}/{a['id']}").status_code,204)
        self.assertEqual(self.client.get(path).json()['items'],[])
        db=connect(self.db)
        self.assertEqual(db.execute('SELECT count(*) FROM wishlist_items').fetchone()[0],2)
        self.assertEqual(db.execute('SELECT count(*) FROM event_wishlist_items').fetchone()[0],0)
        db.close()

    def test_surged_wishlist_item_returns_manual_prices_and_structured_traditional_alternative(self):
        db=connect(self.db)
        language_id=db.execute("SELECT id FROM languages WHERE code='en'").fetchone()[0]
        set_id=db.execute(
            "INSERT INTO sets(game_id,code,name,release_status) VALUES (3,'hob','The Hobbit','released')"
        ).lastrowid
        canonical_id=db.execute(
            "INSERT INTO canonical_cards(game_id,identity_key,name) VALUES (3,'hob:test-card','Test Card A')"
        ).lastrowid
        db.execute("""UPDATE cards SET set_code='hob',set_id=?,card_number='250',language_id=?,
                         treatment='surge_foil',finish='foil',canonical_card_id=?,catalog_status='active'
                      WHERE id=?""",(set_id,language_id,canonical_id,self.ids['card_a_id']))
        db.execute("""UPDATE cards SET set_code='hob',set_id=?,card_number='214',language_id=?,
                         treatment='traditional_foil',finish='foil',canonical_card_id=?,catalog_status='active'
                      WHERE id=?""",(set_id,language_id,canonical_id,self.ids['card_b_id']))
        for card_id,metric,value in [
            (self.ids['card_a_id'],'low',8.25),
            (self.ids['card_a_id'],'avg30',7.75),
            (self.ids['card_b_id'],'low',3.5),
        ]:
            db.execute("""INSERT INTO market_price_observations
                (card_id,provider,market,metric,value,currency,observed_at,snapshot_key,provenance)
                VALUES (?,'cardmarket_manual','cardmarket',?,?,'EUR','2026-09-23T00:00:00Z',
                        'cardmadness-2026-09-23','test fixture')""",(card_id,metric,value))
        db.commit(); db.close()

        target=self.client.post('/api/wishlist',json={'card_id':self.ids['card_a_id']}).json()
        path='/api/events/cardmadness-2026/wishlist'
        self.assertEqual(self.client.post(path,json={'wishlist_item_id':target['id']}).status_code,204)
        item=self.client.get(path).json()['items'][0]
        self.assertEqual(item['wishlist_item']['treatment'],'surge_foil')
        self.assertEqual(item['target_prices'],{'low':8.25,'avg30':7.75})
        self.assertEqual(item['traditional_foil'],{'card_id':self.ids['card_b_id'],'card_number':'214','low':3.5})


if __name__=='__main__': unittest.main()
