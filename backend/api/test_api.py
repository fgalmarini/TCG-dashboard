"""Tests de backend/api/main.py (endpoints) -- TestClient de FastAPI con override de
la dependency de conexion (get_db), nunca tocando el DB_PATH global de produccion."""

import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient

from . import test_support
from .db import connect, get_db
from .main import app


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"
        test_support.make_test_db(self.db_path)

        setup_conn = connect(self.db_path)
        self.ids = test_support.insert_fixtures(setup_conn)
        setup_conn.close()

        def override_get_db():
            conn = connect(self.db_path)
            try:
                yield conn
            finally:
                conn.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.tmp_dir.cleanup()

    def test_overview_endpoint(self):
        resp = self.client.get("/api/overview")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["unique_cards"], 4)
        self.assertEqual(data["total_cards"], 5)
        self.assertEqual(data["cards_without_market_value"]["count"], 2)
        self.assertIn(self.ids["row2_id"], data["cards_without_market_value"]["ids"])
        self.assertIn(self.ids["row3_id"], data["cards_without_market_value"]["ids"])
        self.assertIsNotNone(data["roi"])
        self.assertIn("sin_catalogar", data["value_by_tcg"])
        self.assertLessEqual(len(data["top_cards"]), 10)
        self.assertEqual(data["top_cards"][0]["collection_item_id"], self.ids["row1_id"])
        self.assertEqual(data["top_cards"][0]["price_variation"], 0.25)
        self.assertEqual(data["top_cards"][0]["image"]["source"], "scryfall")

    def test_collection_endpoint_no_filters_returns_all_rows(self):
        resp = self.client.get("/api/collection")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 4)
        self.assertEqual(len(data["items"]), 4)

    def test_collection_endpoint_game_filter(self):
        resp = self.client.get("/api/collection", params={"game": "magic"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["total"], 3)

    def test_collection_endpoint_rows_without_price_show_null_not_zero(self):
        resp = self.client.get("/api/collection")
        items_by_id = {item["id"]: item for item in resp.json()["items"]}
        self.assertIsNone(items_by_id[self.ids["row3_id"]]["market_value"])
        self.assertIsNone(items_by_id[self.ids["row2_id"]]["market_value"])
        self.assertEqual(items_by_id[self.ids["row1_id"]]["market_value"], 12.5)

    def test_collection_endpoint_returns_exact_image_only(self):
        resp = self.client.get("/api/collection")
        items_by_id = {item["id"]: item for item in resp.json()["items"]}

        self.assertEqual(items_by_id[self.ids["row1_id"]]["image"]["source"], "scryfall")
        self.assertEqual(items_by_id[self.ids["row1_id"]]["image"]["match_quality"], "exact")
        self.assertEqual(
            items_by_id[self.ids["row1_id"]]["image"]["faces"][0]["small_url"],
            "https://cards.scryfall.io/small/front/a/a/card-a.jpg",
        )
        self.assertIsNone(items_by_id[self.ids["row2_id"]]["image"])
        self.assertIsNone(items_by_id[self.ids["row3_id"]]["image"])

    def test_collection_endpoint_prefers_scryfall_and_never_calls_network(self):
        conn = connect(self.db_path)
        conn.execute(
            "INSERT INTO card_images (card_id, source, source_card_id, language, face_index, "
            "image_url_small, image_url_large, match_quality, status, last_checked_at) "
            "VALUES (?, 'cardtrader', '9001', 'en', 0, NULL, 'https://cardtrader.com/image.jpg', "
            "'exact', 'resolved', '2026-01-01T00:00:00Z')",
            (self.ids["card_a_id"],),
        )
        conn.commit()
        conn.close()
        with patch("urllib.request.urlopen", side_effect=AssertionError("API no debe hacer network")):
            response = self.client.get("/api/collection")
        self.assertEqual(response.status_code, 200)
        item = next(item for item in response.json()["items"] if item["id"] == self.ids["row1_id"])
        self.assertEqual(item["image"]["source"], "scryfall")

    def test_collection_detail_manual_row_has_null_market_price(self):
        resp = self.client.get(f"/api/collection/{self.ids['row3_id']}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsNone(data["market_price"])
        self.assertTrue(data["manual_entry"])
        self.assertEqual(data["display_name"], data["manual_entry_note"])

    def test_collection_detail_priced_row_shows_source_and_date(self):
        resp = self.client.get(f"/api/collection/{self.ids['row1_id']}")
        data = resp.json()
        self.assertEqual(data["market_price"]["trend"], 12.5)
        self.assertEqual(data["market_price"]["observed_at"], "2026-01-08T00:00:00")
        self.assertEqual(data["market_price"]["source"], "cardmarket")
        self.assertEqual(data["unrealized_pl"], 15.0)
        self.assertEqual(data["roi"], 1.5)
        self.assertEqual(data["image"]["faces"][0]["large_url"], "https://cards.scryfall.io/large/front/a/a/card-a.jpg")

    def test_collection_detail_404_for_missing_id(self):
        resp = self.client.get("/api/collection/999999")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
