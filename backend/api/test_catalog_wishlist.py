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
        self.assertEqual(item["current_price"], 11.0)

    def test_wishlist_lifecycle_and_mark_acquired_without_collection_change(self):
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

        acquired = self.client.post(f"/api/wishlist/{item_id}/mark-acquired")
        self.assertEqual(acquired.status_code, 200)
        self.assertEqual(acquired.json()["status"], "acquired")
        self.assertIsNotNone(acquired.json()["acquired_at"])
        self.assertIsNone(acquired.json()["removed_at"])
        self.assertEqual(self.client.get("/api/wishlist").json()["items"], [])

        conn = connect(self.db_path)
        self.assertEqual(
            conn.execute("SELECT quantity FROM collection_items WHERE card_id=?", (card_id,)).fetchone()[0],
            1,
        )
        self.assertEqual(conn.execute("SELECT status FROM wishlist_items WHERE id=?", (item_id,)).fetchone()[0], "acquired")
        conn.close()

        restored = self.client.post(f"/api/wishlist/{item_id}/restore")
        self.assertEqual(restored.status_code, 200)
        self.assertEqual(restored.json()["status"], "wanted")
        self.assertIsNone(restored.json()["acquired_at"])
        self.assertIsNone(restored.json()["removed_at"])

    def test_delete_is_soft_and_duplicate_active_is_prevented(self):
        card_id = self.ids["card_b_id"]
        created = self.client.post("/api/wishlist", json={"card_id": card_id}).json()
        self.assertEqual(self.client.delete(f"/api/wishlist/{created['id']}").status_code, 204)
        self.assertEqual(self.client.get("/api/wishlist").json()["items"], [])
        conn = connect(self.db_path)
        self.assertEqual(conn.execute("SELECT status FROM wishlist_items").fetchone()[0], "removed")
        self.assertIsNotNone(conn.execute("SELECT removed_at FROM wishlist_items").fetchone()[0])
        conn.close()

    def test_remove_collection_item_deletes_only_possession(self):
        card_id = self.ids["card_a_id"]
        conn = test_support.connect(self.db_path) if hasattr(test_support, "connect") else None
        if conn is None:
            conn = __import__("backend.api.db", fromlist=["connect"]).connect(self.db_path)
        conn.execute("INSERT INTO collection_items(card_id, quantity, status) VALUES (?, 3, 'KEEP')", (card_id,))
        item_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO wishlist_items(card_id) VALUES (?)", (card_id,)); conn.commit(); conn.close()
        self.assertEqual(self.client.delete(f"/api/collection/{item_id}").status_code, 204)
        conn = __import__("backend.api.db", fromlist=["connect"]).connect(self.db_path)
        self.assertIsNone(conn.execute("SELECT 1 FROM collection_items WHERE id=?", (item_id,)).fetchone())
        self.assertIsNotNone(conn.execute("SELECT 1 FROM cards WHERE id=?", (card_id,)).fetchone())
        self.assertIsNotNone(conn.execute("SELECT 1 FROM wishlist_items WHERE card_id=?", (card_id,)).fetchone())
        conn.close()
        self.assertEqual(self.client.delete("/api/collection/999999").status_code, 404)

    def test_summary_is_global_and_estimate_uses_quantity(self):
        card_a = self.ids["card_a_id"]
        card_b = self.ids["card_b_id"]
        first = self.client.post(
            "/api/wishlist",
            json={"card_id": card_a, "quantity_wanted": 3, "priority": "none"},
        ).json()
        second = self.client.post(
            "/api/wishlist",
            json={"card_id": card_b, "quantity_wanted": 2, "max_price": 10, "target_price": 8},
        ).json()
        response = self.client.get("/api/wishlist", params={"priority": "none"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["total"], 1)
        summary = response.json()["summary"]
        self.assertEqual(summary, {
            "wanted": 2,
            "acquired": 0,
            "missing_price": 1,
            "unmatched": 0,
            "estimated_total": 33.0,
        })
        self.assertEqual(first["priority"], "none")
        self.assertEqual(second["target_price"], 8)

    def test_price_order_is_validated_and_csv_uses_filtered_rows(self):
        item = self.client.post("/api/wishlist", json={"card_id": self.ids["card_b_id"]}).json()
        invalid = self.client.patch(
            f"/api/wishlist/{item['id']}",
            json={"target_price": 11, "max_price": 10},
        )
        self.assertEqual(invalid.status_code, 422)
        csv_response = self.client.get("/api/wishlist/export.csv", params={"priority": "medium"})
        self.assertEqual(csv_response.status_code, 200)
        body = csv_response.content.decode("utf-8")
        self.assertIn("game,name,set,collector_number,treatment,finish,language,priority,current_price,current_price_currency,target_price,max_price,status,source,resolution_method", body)
        self.assertEqual(body.count("Test Card B"), 1)

    def test_one_piece_catalog_keeps_language_counts_and_price_provenance(self):
        conn = connect(self.db_path)
        game_id = conn.execute("SELECT id FROM games WHERE code='one_piece'").fetchone()[0]
        jp_id = conn.execute("SELECT id FROM languages WHERE code='jp'").fetchone()[0]
        set_id = conn.execute(
            "INSERT INTO sets (game_id, code, name, release_status) VALUES (?, 'op01', 'Romance Dawn', 'released')",
            (game_id,),
        ).lastrowid
        canonical_id = conn.execute(
            "INSERT INTO canonical_cards (game_id, identity_key, canonical_number, name) VALUES (?, 'OP01-016', 'OP01-016', 'Nami')",
            (game_id,),
        ).lastrowid
        expansion_id = self.ids["expansion_id"]
        en_card = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, canonical_card_id, set_id, card_number, name,
                printing_variant, language_id, release_kind, art_kind, catalog_status)
               VALUES (?, ?, ?, ?, 'OP01-016', 'Nami', 'normal', 1, 'original', 'base', 'active')""",
            (game_id, expansion_id, canonical_id, set_id),
        ).lastrowid
        jp_card = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, canonical_card_id, set_id, card_number, name,
                printing_variant, language_id, release_kind, art_kind, catalog_status)
               VALUES (?, ?, ?, ?, 'OP01-016', 'Nami', 'confirmed_parallel', ?, 'reprint', 'alternate_art', 'active')""",
            (game_id, expansion_id, canonical_id, set_id, jp_id),
        ).lastrowid
        conn.execute(
            """INSERT INTO printing_price_resolutions
               (card_id, language_id, resolved_at, current_price, currency, source,
                resolution_method, sample_size, language_scope)
               VALUES (?, ?, '2026-08-27T00:00:00Z', 7.5, 'EUR', 'cardtrader',
                       'cardtrader_marketplace_low_median_5', 5, 'exact')""",
            (jp_card, jp_id),
        )
        conn.commit(); conn.close()

        result = self.client.get("/api/catalog", params={"game": "one_piece", "language": "jp"})
        self.assertEqual(result.status_code, 200)
        item = result.json()["items"][0]
        self.assertEqual(item["id"], jp_card)
        self.assertEqual(item["printing_count"], 2)
        self.assertEqual(item["reprint_count"], 1)
        self.assertIsNone(item["current_price"])
        self.assertIsNone(item["resolution_method"])

        detail = self.client.get(f"/api/catalog/{jp_card}").json()
        self.assertEqual({row["id"] for row in detail["printings"]}, {en_card, jp_card})
        created = self.client.post("/api/wishlist", json={"card_id": jp_card})
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["language"], "jp")
        self.assertEqual(
            self.client.get("/api/wishlist", params={"game": "one_piece", "language": "en"}).json()["items"],
            [],
        )

    def test_manual_match_relinks_only_selected_collection_row(self):
        conn = connect(self.db_path)
        expansion_id = self.ids["expansion_id"]
        legacy = conn.execute(
            """INSERT INTO cards (game_id, expansion_id, name, printing_variant, set_code, data_source)
               VALUES (3, ?, 'The Bath Song', 'normal', 'ltr', 'manual')""",
            (expansion_id,),
        ).lastrowid
        candidate = conn.execute(
            """INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant,
                                   set_code, normalized_name, finish, language_id, catalog_status)
               VALUES (3, ?, '40', 'The Bath Song', 'normal', 'ltr', 'the bath song', 'nonfoil', 1, 'active')""",
            (expansion_id,),
        ).lastrowid
        product = conn.execute(
            """INSERT INTO cardmarket_products
               (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion,
                date_added, last_seen_at) VALUES (737570, 'The Bath Song', 1, 5285, 'x', 'x')"""
        ).lastrowid
        mapping = conn.execute(
            "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (?, ?, 'mapped')",
            (product, legacy),
        ).lastrowid
        collection_id = conn.execute(
            """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, status, manual_entry)
               VALUES (?, ?, 1, 1, 'KEEP', 0)""",
            (legacy, product),
        ).lastrowid
        conn.commit(); conn.close()

        candidates = self.client.get(f"/api/collection/{collection_id}/match-candidates")
        self.assertEqual(candidates.status_code, 200)
        self.assertTrue(any(row["id"] == candidate for row in candidates.json()["candidates"]))
        resolved = self.client.post(
            f"/api/collection/{collection_id}/resolve-match", json={"card_id": candidate}
        )
        self.assertEqual(resolved.status_code, 200)
        self.assertTrue(resolved.json()["catalog_matched"])

        conn = connect(self.db_path)
        self.assertEqual(conn.execute("SELECT card_id FROM collection_items WHERE id=?", (collection_id,)).fetchone()[0], candidate)
        self.assertEqual(conn.execute("SELECT card_id FROM cardmarket_product_mappings WHERE id=?", (mapping,)).fetchone()[0], candidate)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM collection_items").fetchone()[0], 5)
        conn.close()

    def test_manual_match_preserves_shared_legacy_mapping(self):
        conn = connect(self.db_path)
        expansion_id = self.ids["expansion_id"]
        legacy = conn.execute(
            "INSERT INTO cards (game_id, expansion_id, name, printing_variant, set_code, data_source) VALUES (3, ?, 'Shared Legacy', 'normal', 'ltr', 'manual')",
            (expansion_id,),
        ).lastrowid
        candidate = conn.execute(
            """INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant, set_code, normalized_name, finish, language_id, catalog_status)
               VALUES (3, ?, '99', 'Shared Legacy', 'normal', 'ltr', 'shared legacy', 'foil', 1, 'active')""",
            (expansion_id,),
        ).lastrowid
        product = conn.execute(
            """INSERT INTO cardmarket_products
               (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at)
               VALUES (737571, 'Shared Legacy', 1, 5285, 'x', 'x')"""
        ).lastrowid
        conn.execute(
            "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (?, ?, 'mapped')",
            (product, legacy),
        )
        target = conn.execute(
            "INSERT INTO collection_items (card_id, cardmarket_product_id, language_id, quantity, status) VALUES (?, ?, 1, 1, 'KEEP')",
            (legacy, product),
        ).lastrowid
        other = conn.execute(
            "INSERT INTO collection_items (card_id, cardmarket_product_id, language_id, quantity, status) VALUES (?, ?, 1, 1, 'KEEP')",
            (legacy, product),
        ).lastrowid
        conn.commit(); conn.close()

        response = self.client.post(f"/api/collection/{target}/resolve-match", json={"card_id": candidate})
        self.assertEqual(response.status_code, 200)
        conn = connect(self.db_path)
        self.assertEqual(conn.execute("SELECT card_id FROM collection_items WHERE id=?", (target,)).fetchone()[0], candidate)
        self.assertEqual(conn.execute("SELECT card_id FROM collection_items WHERE id=?", (other,)).fetchone()[0], legacy)
        self.assertEqual(conn.execute("SELECT card_id FROM cardmarket_product_mappings WHERE cardmarket_product_id=?", (product,)).fetchone()[0], legacy)
        conn.close()

    def test_art_series_uses_exact_product_and_excludes_playable_same_name(self):
        conn = connect(self.db_path)
        expansion_id = self.ids["expansion_id"]
        legacy = conn.execute(
            "INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant, set_code) VALUES (3, ?, 'ART-2', 'Art Series: Fog on the Barrow-Downs', 'normal', 'ltr')",
            (expansion_id,),
        ).lastrowid
        art = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant, set_code, normalized_name,
                finish, treatment, source_variant, catalog_status, language_id)
               VALUES (3, ?, 'ART-2', 'Art Series: Fog on the Barrow-Downs', 'normal', 'ltr',
                       'art series: fog on the barrow-downs', 'nonfoil', 'Art Series Gold-Stamped',
                       'art_series_gold_stamped', 'active', 1)""",
            (expansion_id,),
        ).lastrowid
        playable = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant, set_code, normalized_name,
                finish, catalog_status, language_id)
               VALUES (3, ?, '16', 'Fog on the Barrow-Downs', 'normal', 'ltr',
                       'fog on the barrow-downs', 'nonfoil', 'active', 1)""",
            (expansion_id,),
        ).lastrowid
        legacy_duplicate = conn.execute(
            "INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant, set_code) VALUES (3, ?, 'ART-2', 'Art Series: Fog on the Barrow-Downs', 'suggested_parallel', 'ltr')",
            (expansion_id,),
        ).lastrowid
        product = conn.execute(
            """INSERT INTO cardmarket_products
               (cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at)
               VALUES (900001, 'Art Series: Fog on the Barrow-Downs', 1, 5308, 'x', 'x')"""
        ).lastrowid
        conn.execute(
            "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (?, ?, 'mapped')",
            (product, art),
        )
        item = conn.execute(
            """INSERT INTO collection_items
               (card_id, cardmarket_product_id, language_id, quantity, purchase_price, status)
               VALUES (?, ?, 1, 2, 9.5, 'KEEP')""",
            (legacy, product),
        ).lastrowid
        conn.commit(); conn.close()

        response = self.client.get(f"/api/collection/{item}/match-candidates")
        self.assertEqual(response.status_code, 200)
        candidates = response.json()["candidates"]
        self.assertEqual([row["id"] for row in candidates], [art])
        self.assertEqual(candidates[0]["treatment"], "Art Series Gold-Stamped")
        self.assertNotIn(playable, [row["id"] for row in candidates])
        self.assertNotIn(legacy_duplicate, [row["id"] for row in candidates])
        self.assertEqual(
            self.client.post(f"/api/collection/{item}/resolve-match", json={"card_id": legacy_duplicate}).status_code,
            404,
        )

        resolved = self.client.post(f"/api/collection/{item}/resolve-match", json={"card_id": art})
        self.assertEqual(resolved.status_code, 200)
        self.assertTrue(resolved.json()["catalog_matched"])
        self.assertEqual(resolved.json()["treatment"], "Art Series Gold-Stamped")
        self.assertEqual(resolved.json()["source_variant"], "art_series_gold_stamped")
        self.assertEqual(resolved.json()["finish"], "nonfoil")
        conn = connect(self.db_path)
        self.assertEqual(tuple(conn.execute("SELECT card_id, quantity, purchase_price FROM collection_items WHERE id=?", (item,)).fetchone()), (art, 2, 9.5))
        conn.close()

    def test_art_series_resolve_rejects_playable_candidate(self):
        conn = connect(self.db_path)
        expansion_id = self.ids["expansion_id"]
        legacy = conn.execute(
            "INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant, set_code) VALUES (3, ?, 'ART-9', 'Art Series: A Test', 'normal', 'ltr')",
            (expansion_id,),
        ).lastrowid
        playable = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant, set_code, finish, catalog_status, language_id)
               VALUES (3, ?, '9', 'A Test', 'normal', 'ltr', 'nonfoil', 'active', 1)""",
            (expansion_id,),
        ).lastrowid
        item = conn.execute("INSERT INTO collection_items (card_id, language_id, quantity, status) VALUES (?, 1, 1, 'KEEP')", (legacy,)).lastrowid
        conn.commit(); conn.close()
        response = self.client.post(f"/api/collection/{item}/resolve-match", json={"card_id": playable})
        self.assertEqual(response.status_code, 422)

    def test_art_series_fallback_matches_set_name_and_art_number(self):
        conn = connect(self.db_path)
        expansion_id = self.ids["expansion_id"]
        legacy = conn.execute(
            "INSERT INTO cards (game_id, expansion_id, card_number, name, printing_variant, set_code) VALUES (3, ?, 'ART-7', 'Art Series: Exact Fallback', 'normal', 'ltr')",
            (expansion_id,),
        ).lastrowid
        art = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant, set_code, normalized_name,
                finish, catalog_status, language_id)
               VALUES (3, ?, 'ART-7', 'Art Series: Exact Fallback', 'normal', 'ltr',
                       'art series: exact fallback', 'nonfoil', 'active', 1)""",
            (expansion_id,),
        ).lastrowid
        playable = conn.execute(
            """INSERT INTO cards
               (game_id, expansion_id, card_number, name, printing_variant, set_code, normalized_name,
                finish, catalog_status, language_id)
               VALUES (3, ?, '7', 'Exact Fallback', 'normal', 'ltr',
                       'exact fallback', 'nonfoil', 'active', 1)""",
            (expansion_id,),
        ).lastrowid
        item = conn.execute("INSERT INTO collection_items (card_id, language_id, quantity, status) VALUES (?, 1, 1, 'KEEP')", (legacy,)).lastrowid
        conn.commit(); conn.close()

        response = self.client.get(f"/api/collection/{item}/match-candidates")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.json()["candidates"]], [art])
        self.assertNotIn(playable, [row["id"] for row in response.json()["candidates"]])


if __name__ == "__main__":
    unittest.main()
