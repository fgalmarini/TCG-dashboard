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


if __name__=='__main__': unittest.main()
