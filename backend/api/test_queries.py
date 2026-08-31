"""Tests de backend/api/queries.py -- DB temporal con schema.sql+seed.sql reales +
fixtures a mano (backend/api/test_support.py), mismo patron que
backend/scripts/test_scryfall_backfill.py."""

import tempfile
import unittest
from pathlib import Path

from . import queries, test_support
from .db import connect


class QueriesTest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp_dir.name) / "test.db"
        test_support.make_test_db(self.db_path)
        self.conn = connect(self.db_path)
        self.ids = test_support.insert_fixtures(self.conn)

    def tearDown(self):
        self.conn.close()
        self.tmp_dir.cleanup()

    def test_latest_price_snapshot_picks_max_observed_at(self):
        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row1_id"])
        self.assertEqual(row.market_trend, 11.0)
        self.assertEqual(row.price_observed_at, "2026-01-08T00:00:00")

    def _insert_resolution(self, *, card_id, resolved_at, current_price, is_current, source="cardmarket"):
        self.conn.execute(
            """INSERT INTO printing_price_resolutions
               (card_id, language_id, resolved_at, current_price, currency, source,
                resolution_method, match_status, is_current)
               VALUES (?, 1, ?, ?, 'EUR', ?, 'cardmarket_exact_language', 'EXACT', ?)""",
            (card_id, resolved_at, current_price, source, is_current),
        )
        self.conn.commit()

    def test_collection_one_row_with_multiple_historical_resolutions(self):
        card_id = self.ids["card_a_id"]
        self._insert_resolution(card_id=card_id, resolved_at="2026-01-01T00:00:00", current_price=8.0, is_current=0)
        self._insert_resolution(card_id=card_id, resolved_at="2026-01-07T00:00:00", current_price=9.0, is_current=0)
        self._insert_resolution(card_id=card_id, resolved_at="2026-01-09T00:00:00", current_price=10.0, is_current=1)
        rows = queries.fetch_collection_rows(self.conn)
        matching = [row for row in rows if row.id == self.ids["row1_id"]]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].quantity, 2)
        self.assertEqual(matching[0].market_trend, 10.0)

    def test_collection_current_null_resolution_is_one_row_and_wins_history(self):
        card_id = self.ids["card_a_id"]
        self._insert_resolution(card_id=card_id, resolved_at="2026-01-01T00:00:00", current_price=8.0, is_current=0)
        self._insert_resolution(card_id=card_id, resolved_at="2026-01-09T00:00:00", current_price=None, is_current=1)
        rows = queries.fetch_collection_rows(self.conn)
        matching = [row for row in rows if row.id == self.ids["row1_id"]]
        self.assertEqual(len(matching), 1)
        self.assertIsNone(matching[0].market_trend)

    def test_legacy_schema_chooses_one_latest_resolution_instead_of_all_history(self):
        legacy_path = Path(self.tmp_dir.name) / "legacy.db"
        test_support.make_test_db(legacy_path)
        legacy_conn = connect(legacy_path)
        ids = test_support.insert_fixtures(legacy_conn)
        for index, price in enumerate((8.0, 9.0, 10.0), start=1):
            legacy_conn.execute(
                """INSERT INTO printing_price_resolutions
                   (card_id, language_id, resolved_at, current_price, currency,
                    source, resolution_method)
                   VALUES (?, 1, ?, ?, 'EUR', 'cardmarket',
                           'cardmarket_exact_language')""",
                (ids["card_a_id"], f"2026-01-0{index}T00:00:00", price),
            )
        legacy_conn.execute("DROP INDEX idx_printing_price_current_identity")
        legacy_conn.execute("DROP INDEX IF EXISTS idx_wishlist_price_current_item")
        for column in (
            "provenance", "source_manifest_id", "source_snapshot_sha256",
            "source_snapshot_created_at", "source_currency", "cardmarket_foil_avg30",
            "cardmarket_foil_avg7", "cardmarket_foil_avg1", "cardmarket_foil_trend",
            "cardmarket_foil_low", "cardmarket_avg30", "cardmarket_avg7",
            "cardmarket_avg1", "cardmarket_trend", "cardmarket_low", "selected_metric",
            "is_current", "match_status", "cardmarket_product_id",
        ):
            legacy_conn.execute(f"ALTER TABLE printing_price_resolutions DROP COLUMN {column}")
        legacy_conn.commit()
        legacy_conn.close()

        reopened = connect(legacy_path)
        rows = queries.fetch_collection_rows(reopened)
        matching = [row for row in rows if row.id == ids["row1_id"]]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].market_trend, 10.0)
        reopened.close()

    def test_collection_catalog_and_wishlist_have_no_pricing_join_multiplication(self):
        card_id = self.ids["card_a_id"]
        self.conn.execute("UPDATE cards SET finish='nonfoil' WHERE id=?", (card_id,))
        self.conn.commit()
        for index, price in enumerate((8.0, 9.0, 10.0), start=1):
            self._insert_resolution(
                card_id=card_id,
                resolved_at=f"2026-01-0{index}T00:00:00",
                current_price=price,
                is_current=1 if index == 3 else 0,
            )
        self.conn.execute(
            "INSERT INTO wishlist_items (card_id, language_id, quantity_wanted, status) VALUES (?, 1, 1, 'wanted')",
            (card_id,),
        )
        self.conn.commit()

        collection_rows = queries.fetch_collection_rows(self.conn)
        where, params = queries.build_catalog_filters(game="magic")
        catalog_rows = queries.fetch_catalog_rows(self.conn, where, params, 1000, 0)
        wishlist_rows = queries.fetch_wishlist_rows(self.conn, status="wanted", game="magic")
        self.assertEqual(sum(row.id == self.ids["row1_id"] for row in collection_rows), 1)
        self.assertEqual(sum(row.id == card_id for row in catalog_rows), 1)
        self.assertEqual(sum(row.card_id == card_id for row in wishlist_rows), 1)

    def test_wishlist_current_null_resolution_blocks_global_fallback(self):
        card_id = self.ids["card_a_id"]
        self.conn.execute(
            "INSERT INTO wishlist_items (card_id, language_id, quantity_wanted, status) VALUES (?, 1, 1, 'wanted')",
            (card_id,),
        )
        wishlist_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self._insert_resolution(card_id=card_id, resolved_at="2026-01-10T00:00:00", current_price=99.0, is_current=1)
        self.conn.execute(
            """INSERT INTO printing_price_resolutions
               (card_id, wishlist_item_id, resolution_scope, language_id,
                resolved_at, current_price, currency, source, resolution_method,
                match_status, is_current)
               VALUES (?, ?, 'wishlist', 1, '2026-01-11T00:00:00', NULL, 'EUR',
                       'cardmarket', 'no_exact_language_price', 'AMBIGUOUS', 1)""",
            (card_id, wishlist_id),
        )
        self.conn.commit()
        rows = queries.fetch_wishlist_rows(self.conn, status="wanted", game="magic")
        matching = [row for row in rows if row.id == wishlist_id]
        self.assertEqual(len(matching), 1)
        self.assertIsNone(matching[0].current_price)
        self.assertIsNone(matching[0].cardmarket_low)
        self.assertIsNone(matching[0].source)
        self.assertIsNone(matching[0].resolution_method)

    def test_wishlist_foil_resolution_exposes_selected_low_not_base_low(self):
        card_id = self.ids["card_a_id"]
        self.conn.execute("UPDATE cards SET finish='foil' WHERE id=?", (card_id,))
        self.conn.execute(
            "INSERT INTO wishlist_items (card_id, language_id, quantity_wanted, status) VALUES (?, 1, 1, 'wanted')",
            (card_id,),
        )
        wishlist_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        self.conn.execute(
            """INSERT INTO printing_price_resolutions
               (card_id, wishlist_item_id, resolution_scope, language_id,
                resolved_at, current_price, currency, source, resolution_method,
                match_status, is_current, selected_metric, cardmarket_low,
                cardmarket_trend, cardmarket_avg7, cardmarket_foil_low,
                cardmarket_foil_trend, cardmarket_foil_avg7, source_currency)
               VALUES (?, ?, 'wishlist', 1, '2026-01-11T00:00:00', 14.5, 'EUR',
                       'cardmarket', 'cardmarket_exact_language', 'EXACT', 1,
                       'Foil Low', 10.0, 11.0, 12.0, 14.5, 15.5, 16.5, 'EUR')""",
            (card_id, wishlist_id),
        )
        self.conn.commit()
        rows = queries.fetch_wishlist_rows(self.conn, status="wanted", game="magic")
        matching = [row for row in rows if row.id == wishlist_id]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].current_price, 14.5)
        self.assertEqual(matching[0].cardmarket_low, 14.5)
        self.assertEqual(matching[0].cardmarket_trend, 15.5)
        self.assertEqual(matching[0].cardmarket_avg7, 16.5)
        self.assertEqual(matching[0].source, "cardmarket")

    def test_product_without_snapshot_has_null_market_trend_and_is_not_manual(self):
        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row2_id"])
        self.assertIsNone(row.market_trend)
        self.assertFalse(row.manual_entry)
        self.assertIsNone(row.treatment)
        self.assertIsNone(row.source_variant)
        self.assertIsNone(row.finish)

    def test_collection_row_exposes_card_treatment_variant_and_finish(self):
        self.conn.execute(
            "UPDATE cards SET treatment='Art Series Gold-Stamped', source_variant='art_series_gold_stamped', finish='nonfoil' WHERE id=?",
            (self.ids["card_a_id"],),
        )
        self.conn.commit()
        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row1_id"])
        self.assertEqual(row.treatment, "Art Series Gold-Stamped")
        self.assertEqual(row.source_variant, "art_series_gold_stamped")
        self.assertEqual(row.finish, "nonfoil")

    def test_foil_price_falls_back_to_alt_metric_when_base_trend_is_zero(self):
        product_id = 2003
        self.conn.execute(
            """INSERT INTO cardmarket_products
                   (id, cardmarket_id_product, raw_name, cardmarket_id_category,
                    cardmarket_id_expansion, date_added, last_seen_at)
               VALUES (?, 900003, 'Foil Product', 1, 5285, '2026-01-01', '2026-01-01')""",
            (product_id,),
        )
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, trend_alt, avg30_alt, imported_at)
               VALUES (?, '2026-01-09T00:00:00', 0, 7.25, 7.0, '2026-01-09T00:00:00')""",
            (product_id,),
        )
        self.conn.execute(
            """INSERT INTO collection_items
                   (card_id, cardmarket_product_id, language_id, quantity, status, manual_entry)
               VALUES (?, ?, 1, 1, 'KEEP', 0)""",
            (self.ids["card_a_id"], product_id),
        )
        row_id = self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        row = queries.fetch_collection_row_by_id(self.conn, row_id)
        self.assertIsNone(row.market_trend)
        self.assertEqual(row.market_avg30, 7.0)

    def test_manual_row_has_null_market_trend_and_display_name_from_note(self):
        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row3_id"])
        self.assertIsNone(row.market_trend)
        self.assertTrue(row.manual_entry)
        self.assertIsNone(row.card_name)
        self.assertEqual(row.display_name, row.manual_entry_note)

    def test_row_missing_purchase_price_but_with_market_value(self):
        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row4_id"])
        self.assertIsNone(row.purchase_price)
        self.assertEqual(row.market_trend, 11.0)

    def test_fetch_collection_row_by_id_returns_none_for_missing_id(self):
        self.assertIsNone(queries.fetch_collection_row_by_id(self.conn, 999999))

    def test_fetch_collection_rows_attaches_exact_images_in_batch(self):
        rows = queries.fetch_collection_rows(self.conn, include_images=True)
        rows_by_id = {row.id: row for row in rows}

        self.assertIsNotNone(rows_by_id[self.ids["row1_id"]].image)
        self.assertEqual(rows_by_id[self.ids["row1_id"]].image.faces[0].face_index, 0)
        self.assertEqual(
            rows_by_id[self.ids["row1_id"]].image.faces[0].small_url,
            "https://cards.scryfall.io/small/front/a/a/card-a.jpg",
        )

    def test_fetch_collection_rows_hides_representative_images(self):
        rows = queries.fetch_collection_rows(self.conn, include_images=True)
        rows_by_id = {row.id: row for row in rows}

        self.assertIsNone(rows_by_id[self.ids["row2_id"]].image)

    def test_fetch_collection_rows_uses_cardtrader_when_scryfall_is_not_exact(self):
        self.conn.execute(
            "UPDATE card_images SET source = 'cardtrader', source_card_id = '9001', "
            "image_url_small = NULL, image_url_large = 'https://cardtrader.com/image.jpg', "
            "match_quality = 'exact' WHERE card_id = ?",
            (self.ids["card_b_id"],),
        )
        self.conn.commit()
        rows = queries.fetch_collection_rows(self.conn, include_images=True)
        rows_by_id = {row.id: row for row in rows}
        image = rows_by_id[self.ids["row2_id"]].image
        self.assertIsNotNone(image)
        self.assertEqual(image.source, "cardtrader")
        self.assertIsNone(image.faces[0].small_url)
        self.assertEqual(image.faces[0].large_url, "https://cardtrader.com/image.jpg")

    def test_compute_overview_totals(self):
        data = queries.compute_overview(self.conn)
        self.assertEqual(data.unique_cards, 4)
        self.assertEqual(data.total_cards, 5)  # 2+1+1+1
        self.assertAlmostEqual(data.total_cost, 10.0 + 3.0 + 20.0)  # row4 sin purchase_price
        self.assertEqual(data.cost_basis_row_count, 3)
        self.assertEqual(data.rows_without_cost, 1)
        self.assertAlmostEqual(data.total_market_value, 2 * 11.0 + 1 * 11.0)  # row1 + row4
        self.assertEqual(data.market_value_row_count, 2)
        self.assertAlmostEqual(data.unrealized_pl, (2 * 11.0 + 11.0) - 33.0)
        self.assertAlmostEqual(data.roi, ((2 * 11.0 + 11.0) - 33.0) / 33.0)

    def test_compute_overview_cards_without_market_value_includes_no_snapshot_and_manual(self):
        data = queries.compute_overview(self.conn)
        self.assertEqual(data.cards_without_market_value_count, 2)
        self.assertIn(self.ids["row2_id"], data.cards_without_market_value_ids)
        self.assertIn(self.ids["row3_id"], data.cards_without_market_value_ids)

    def test_compute_overview_top_cards_uses_copy_price_and_previous_snapshot(self):
        self.conn.execute(
            "UPDATE collection_items SET quantity=100 WHERE id=?",
            (self.ids["row2_id"],),
        )
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-08T00:00:00', 11.0, '2026-01-08T00:00:00')""",
            (self.ids["product_b_id"],),
        )
        self.conn.commit()

        data = queries.compute_overview(self.conn)

        self.assertEqual([row.id for row in data.top_cards], [self.ids["row1_id"], self.ids["row4_id"]])
        self.assertEqual(data.top_cards[0].market_trend, 11.0)
        self.assertAlmostEqual(data.top_cards[0].price_variation, 0.1)
        self.assertIsNotNone(data.top_cards[0].image)

    def test_top_cards_ignores_zero_previous_snapshot(self):
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-01T00:00:00', 0, '2026-01-01T00:00:00')""",
            (self.ids["product_b_id"],),
        )
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-08T00:00:00', 11.0, '2026-01-08T00:00:00')""",
            (self.ids["product_b_id"],),
        )
        self.conn.commit()

        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row2_id"])

        assert row is not None
        self.assertIsNone(row.market_trend)
        self.assertIsNone(row.previous_market_trend)
        self.assertIsNone(row.price_variation)

    def test_top_cards_calculates_negative_variation(self):
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-01T00:00:00', 20.0, '2026-01-01T00:00:00')""",
            (self.ids["product_b_id"],),
        )
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-08T00:00:00', 10.0, '2026-01-08T00:00:00')""",
            (self.ids["product_b_id"],),
        )
        self.conn.commit()

        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row2_id"])

        assert row is not None
        self.assertIsNone(row.price_variation)

    def test_top_cards_calculates_zero_variation_after_intermediate_invalid_snapshot(self):
        for observed_at, trend in (
            ("2026-01-01T00:00:00", 10.0),
            ("2026-01-04T00:00:00", 0.0),
            ("2026-01-08T00:00:00", 10.0),
        ):
            self.conn.execute(
                """INSERT INTO market_price_history
                       (cardmarket_product_id, observed_at, trend, imported_at)
                   VALUES (?, ?, ?, ?)""",
                (self.ids["product_b_id"], observed_at, trend, observed_at),
            )
        self.conn.commit()

        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row2_id"])

        assert row is not None
        self.assertIsNone(row.market_trend)
        self.assertEqual(row.previous_market_trend, 10.0)
        self.assertIsNone(row.price_variation)

    def test_top_cards_with_only_one_valid_snapshot_has_null_variation(self):
        self.conn.execute(
            """INSERT INTO market_price_history
                   (cardmarket_product_id, observed_at, trend, imported_at)
               VALUES (?, '2026-01-08T00:00:00', 10.0, '2026-01-08T00:00:00')""",
            (self.ids["product_b_id"],),
        )
        self.conn.commit()

        row = queries.fetch_collection_row_by_id(self.conn, self.ids["row2_id"])

        assert row is not None
        self.assertIsNone(row.previous_market_trend)
        self.assertIsNone(row.price_variation)

    def test_compute_overview_roi_none_when_total_cost_zero(self):
        tmp_dir2 = tempfile.TemporaryDirectory()
        try:
            db_path2 = Path(tmp_dir2.name) / "test2.db"
            test_support.make_test_db(db_path2)
            conn2 = connect(db_path2)
            conn2.execute(
                "INSERT INTO collection_items "
                "(card_id, cardmarket_product_id, language_id, quantity, purchase_price, status, manual_entry) "
                "VALUES (NULL, NULL, 1, 1, NULL, 'KEEP', 1)"
            )
            conn2.commit()
            data = queries.compute_overview(conn2)
            self.assertEqual(data.total_cost, 0.0)
            self.assertIsNone(data.roi)
            conn2.close()
        finally:
            tmp_dir2.cleanup()

    def test_value_by_tcg_includes_sin_catalogar_bucket_without_inventing_value(self):
        data = queries.compute_overview(self.conn)
        self.assertIn("magic", data.value_by_tcg)
        self.assertIn("sin_catalogar", data.value_by_tcg)
        self.assertEqual(data.value_by_tcg["sin_catalogar"].unique_cards, 1)
        self.assertEqual(data.value_by_tcg["sin_catalogar"].market_value, 0.0)

    def test_sort_by_valor_does_not_intermix_null_rows(self):
        where_sql, params = queries.build_collection_filters()
        order_by_sql = queries.build_order_by("valor")
        rows = queries.fetch_collection_rows(
            self.conn, where_sql=where_sql, where_params=params, order_by_sql=order_by_sql
        )
        trends = [r.market_trend for r in rows]
        first_null_index = next((i for i, t in enumerate(trends) if t is None), None)
        self.assertIsNotNone(first_null_index)
        self.assertTrue(all(t is not None for t in trends[:first_null_index]))
        self.assertTrue(all(t is None for t in trends[first_null_index:]))

    def test_search_reaches_manual_rows_via_manual_entry_note(self):
        where_sql, params = queries.build_collection_filters(search="Some Promo Card")
        rows = queries.fetch_collection_rows(self.conn, where_sql=where_sql, where_params=params)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].id, self.ids["row3_id"])

    def test_game_filter_excludes_manual_row(self):
        where_sql, params = queries.build_collection_filters(game="magic")
        total = queries.count_collection_rows(self.conn, where_sql, params)
        self.assertEqual(total, 3)  # row1, row2, row4 -- row3 (manual) no tiene game_id resoluble

    def test_status_filter(self):
        where_sql, params = queries.build_collection_filters(status="HOLD")
        total = queries.count_collection_rows(self.conn, where_sql, params)
        self.assertEqual(total, 1)  # solo row4


if __name__ == "__main__":
    unittest.main()
