import unittest

from fastapi.testclient import TestClient

from . import test_support
from .db import connect, get_db
from .main import app


class CatalogWishlistApiTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        from pathlib import Path

        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        test_support.make_test_db(self.db_path)
        conn = connect(self.db_path)
        self.ids = test_support.insert_fixtures(conn)
        conn.execute(
            """UPDATE cards SET set_code='ltr', normalized_name=lower(name),
               finish='nonfoil', language_id=1 WHERE id IN (?, ?)""",
            (self.ids["card_a_id"], self.ids["card_b_id"]),
        )
        conn.commit(); conn.close()

        def override_get_db():
            db = connect(self.db_path)
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.tmp.cleanup()

    def test_catalog_search_and_ownership(self):
        response = self.client.get("/api/catalog", params={"search": "Test Card A"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        item = response.json()["items"][0]
        self.assertEqual(item["ownership_status"], "owned")
        self.assertEqual(item["current_price"], 12.5)

    def test_wishlist_lifecycle_and_move_to_collection(self):
        card_id = self.ids["card_b_id"]
        created = self.client.post("/api/wishlist", json={"card_id": card_id})
        self.assertEqual(created.status_code, 201)
        item = created.json()
        self.assertEqual(item["priority"], "medium")
        item_id = item["id"]

        duplicate = self.client.post("/api/wishlist", json={"card_id": card_id})
        self.assertEqual(duplicate.status_code, 201)
        self.assertEqual(duplicate.json()["id"], item_id)
        self.assertEqual(self.client.get("/api/wishlist").json()["items"][0]["id"], item_id)

        updated = self.client.patch(f"/api/wishlist/{item_id}", json={"priority": "high"})
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["priority"], "high")

        moved = self.client.post(f"/api/wishlist/{item_id}/move-to-collection")
        self.assertEqual(moved.status_code, 200)
        self.assertEqual(moved.json()["status"], "acquired")
        self.assertEqual(self.client.get("/api/wishlist").json()["items"], [])

        conn = connect(self.db_path)
        self.assertEqual(
            conn.execute("SELECT quantity FROM collection_items WHERE card_id=?", (card_id,)).fetchone()[0],
            2,
        )
        self.assertEqual(conn.execute("SELECT status FROM wishlist_items WHERE id=?", (item_id,)).fetchone()[0], "acquired")
        conn.close()

    def test_delete_is_soft_and_duplicate_active_is_prevented(self):
        card_id = self.ids["card_b_id"]
        created = self.client.post("/api/wishlist", json={"card_id": card_id}).json()
        self.assertEqual(self.client.delete(f"/api/wishlist/{created['id']}").status_code, 204)
        self.assertEqual(self.client.get("/api/wishlist").json()["items"], [])
        conn = connect(self.db_path)
        self.assertEqual(conn.execute("SELECT status FROM wishlist_items").fetchone()[0], "removed")
        conn.close()


if __name__ == "__main__":
    unittest.main()
