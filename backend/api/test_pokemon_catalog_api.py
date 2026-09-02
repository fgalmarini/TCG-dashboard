import sqlite3
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from .db import connect, get_db
from .main import app
from backend.scripts import import_pokemon_151


class PokemonCatalogApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "catalog.db"
        conn = sqlite3.connect(self.db)
        root = Path(__file__).resolve().parents[2]
        conn.executescript((root / "backend/db/schema.sql").read_text())
        conn.executescript((root / "backend/db/seed.sql").read_text())
        conn.commit(); conn.close()
        import_pokemon_151.run(
            self.db,
            Path(__file__).resolve().parents[2] / "reports/pokemon_151/identity_discovery",
            Path(self.tmp.name) / "reports",
            Path(self.tmp.name) / "backups",
            True,
        )

        def override_get_db():
            conn = connect(self.db)
            try:
                yield conn
            finally:
                conn.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.tmp.cleanup()

    def test_pokemon_set_and_finish_filters_expose_numbered_identity_count(self):
        response = self.client.get("/api/catalog", params={"game": "pokemon", "sets": "mew"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 362)
        self.assertEqual(payload["identity_total"], 207)
        self.assertEqual(self.client.get("/api/catalog", params={"game": "pokemon", "sets": "mew", "finish": "holo"}).json()["total"], 81)
        self.assertEqual(self.client.get("/api/catalog/options", params={"game": "pokemon"}).json()["sets"], [{"value": "mew", "label": "Scarlet & Violet—151"}])

    def test_catalog_returns_exact_numbered_images_and_null_prices(self):
        all_numbers = set()
        for page in range(1, 10):
            response = self.client.get("/api/catalog", params={"game": "pokemon", "sets": "mew", "page": page, "page_size": 100})
            self.assertEqual(response.status_code, 200)
            for item in response.json()["items"]:
                all_numbers.add(item["card_number"])
                self.assertEqual(item["image"]["source"], "tcgdex")
                self.assertIsNone(item["current_price"])
                self.assertIsNone(item["price_source"])
        self.assertEqual(all_numbers, {f"{number:03d}" for number in range(1, 208)})

    def test_catalog_exposes_secondary_prices_without_promoting_them(self):
        conn = connect(self.db)
        try:
            card_id = conn.execute("SELECT id FROM cards WHERE set_code='mew' AND card_number='001' AND finish='normal'").fetchone()[0]
            conn.execute("""
                INSERT INTO market_price_observations
                  (card_id, provider, market, metric, value, currency, source_updated_at,
                   observed_at, snapshot_key, provenance, confidence, source_variant)
                VALUES (?, 'pokemon_tcg_api', 'tcgplayer', 'market', 0.26, 'USD',
                        '2026/09/01', '2026-09-01T13:02:34+00:00', 'fixture', '{}', 'medium', 'normal')
            """, (card_id,))
            conn.execute("""
                INSERT INTO market_price_observations
                  (card_id, provider, market, metric, value, currency, source_updated_at,
                   observed_at, snapshot_key, provenance, confidence, source_variant)
                VALUES (?, 'pokemon_tcg_api', 'tcgplayer', 'low', 0.01, 'USD',
                        '2026/09/01', '2026-09-01T13:02:34+00:00', 'fixture', '{}', 'medium', 'normal')
            """, (card_id,))
            conn.commit()
        finally:
            conn.close()
        response = self.client.get(f"/api/catalog/{card_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["printing"]
        self.assertIsNone(payload["current_price"])
        self.assertEqual(payload["price_sources"][0]["market"], "tcgplayer")
        self.assertEqual(payload["price_sources"][0]["metrics"], {"market": 0.26, "low": 0.01})
        self.assertEqual(payload["price_sources"][0]["currency"], "USD")

    def test_pokemon_catalog_card_can_be_added_to_collection_and_wishlist(self):
        conn = connect(self.db)
        try:
            card_id = conn.execute(
                "SELECT id FROM cards WHERE set_code='mew' AND card_number='054' AND finish='reverse_holo'"
            ).fetchone()[0]
        finally:
            conn.close()

        collection_response = self.client.post("/api/collection", json={"card_id": card_id, "quantity": 1})
        self.assertEqual(collection_response.status_code, 201)
        collection_item = collection_response.json()
        self.assertEqual(collection_item["game_code"], "pokemon")
        self.assertEqual(collection_item["card_number"], "054")
        self.assertEqual(collection_item["finish"], "reverse_holo")
        self.assertEqual(collection_item["quantity"], 1)

        wishlist_response = self.client.post("/api/wishlist", json={"card_id": card_id})
        self.assertEqual(wishlist_response.status_code, 201)
        wishlist_item = wishlist_response.json()
        self.assertEqual(wishlist_item["game_code"], "pokemon")
        self.assertEqual(wishlist_item["card_number"], "054")
        self.assertEqual(wishlist_item["finish"], "reverse_holo")
        self.assertEqual(wishlist_item["status"], "wanted")

        catalog_response = self.client.get(f"/api/catalog/{card_id}")
        self.assertEqual(catalog_response.status_code, 200)
        catalog_item = catalog_response.json()["printing"]
        self.assertTrue(catalog_item["owned"])
        self.assertTrue(catalog_item["wishlist"])
        self.assertEqual(catalog_item["ownership_status"], "owned_wishlist")


if __name__ == "__main__":
    unittest.main()
