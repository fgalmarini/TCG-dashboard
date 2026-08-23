import unittest

from price_history import insert_for_referenced_products
from report import ImportReport
from test_support import make_test_db


class PriceHistoryTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_test_db()
        self.conn.execute(
            "INSERT INTO cardmarket_products (id, cardmarket_id_product, raw_name, cardmarket_id_category, cardmarket_id_expansion, date_added, last_seen_at) "
            "VALUES (1, 701675, 'Gandalf the Grey', 1, 5285, '2023-01-01', '2026-01-01')"
        )
        self.price_index = {701675: {"avg": 0.31, "low": 0.03, "trend": 0.31, "avg1": 0.26, "avg7": 0.39, "avg30": 0.34}}
        self.report = ImportReport()

    def tearDown(self):
        self.conn.close()

    def test_no_references_inserts_nothing(self):
        # esperado: Fase 5 (coleccion manual) todavia no existe -> 0 filas.
        count = insert_for_referenced_products(
            self.conn, self.price_index, "-foil", "2026-01-01T00:00:00", "2026-01-02T00:00:00", "magic", self.report
        )
        self.assertEqual(count, 0)
        self.assertEqual(self.report.price_history_inserted["magic"], 0)

    def test_referenced_from_collection_items_inserts_row(self):
        self.conn.execute(
            "INSERT INTO collection_items (cardmarket_product_id, status) VALUES (1, 'KEEP')"
        )
        count = insert_for_referenced_products(
            self.conn, self.price_index, "-foil", "2026-01-01T00:00:00", "2026-01-02T00:00:00", "magic", self.report
        )
        self.assertEqual(count, 1)
        row = self.conn.execute(
            "SELECT low, avg, observed_at FROM market_price_history WHERE cardmarket_product_id = 1"
        ).fetchone()
        self.assertEqual(row, (0.03, 0.31, "2026-01-01T00:00:00"))

    def test_referenced_from_want_list_via_mapping(self):
        self.conn.execute("INSERT INTO expansions (id, game_id, cardmarket_id_expansion) VALUES (1, 3, 5285)")
        self.conn.execute(
            "INSERT INTO cards (id, game_id, expansion_id, name, printing_variant) "
            "VALUES (1, 3, 1, 'Gandalf the Grey', 'normal')"
        )
        self.conn.execute(
            "INSERT INTO cardmarket_product_mappings (cardmarket_product_id, card_id, status) VALUES (1, 1, 'mapped')"
        )
        self.conn.execute("INSERT INTO want_list_items (card_id, priority) VALUES (1, 'MEDIUM')")
        count = insert_for_referenced_products(
            self.conn, self.price_index, "-foil", "2026-01-01T00:00:00", "2026-01-02T00:00:00", "magic", self.report
        )
        self.assertEqual(count, 1)

    def test_second_run_same_observed_at_does_not_duplicate(self):
        self.conn.execute("INSERT INTO collection_items (cardmarket_product_id, status) VALUES (1, 'KEEP')")
        insert_for_referenced_products(self.conn, self.price_index, "-foil", "2026-01-01T00:00:00", "t1", "magic", self.report)
        insert_for_referenced_products(self.conn, self.price_index, "-foil", "2026-01-01T00:00:00", "t2", "magic", self.report)
        count = self.conn.execute("SELECT COUNT(*) FROM market_price_history").fetchone()[0]
        self.assertEqual(count, 1)


if __name__ == "__main__":
    unittest.main()
