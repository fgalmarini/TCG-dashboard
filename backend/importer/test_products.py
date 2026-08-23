import unittest

from products import upsert_product
from test_support import make_test_db


class ProductsTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_test_db()

    def tearDown(self):
        self.conn.close()

    def test_insert_new_product(self):
        local_id = upsert_product(
            self.conn, cardmarket_id_product=701675, raw_name="Gandalf the Grey",
            cardmarket_id_category=1, cardmarket_id_expansion=5285, cardmarket_id_metacard=417593,
            date_added="2023-03-14 09:32:42", last_seen_at="2026-08-22T10:58:20+0200",
        )
        row = self.conn.execute("SELECT raw_name, date_added FROM cardmarket_products WHERE id = ?", (local_id,)).fetchone()
        self.assertEqual(row[0], "Gandalf the Grey")
        self.assertEqual(row[1], "2023-03-14 09:32:42")

    def test_second_run_upserts_without_duplicating(self):
        first_id = upsert_product(
            self.conn, cardmarket_id_product=701675, raw_name="Gandalf the Grey",
            cardmarket_id_category=1, cardmarket_id_expansion=5285, cardmarket_id_metacard=417593,
            date_added="2023-03-14 09:32:42", last_seen_at="2026-08-22T10:00:00+0200",
        )
        second_id = upsert_product(
            self.conn, cardmarket_id_product=701675, raw_name="Gandalf the Grey",
            cardmarket_id_category=1, cardmarket_id_expansion=5285, cardmarket_id_metacard=417593,
            date_added="2023-03-14 09:32:42", last_seen_at="2026-08-23T10:00:00+0200",
        )
        self.assertEqual(first_id, second_id)
        count = self.conn.execute("SELECT COUNT(*) FROM cardmarket_products").fetchone()[0]
        self.assertEqual(count, 1)
        last_seen = self.conn.execute("SELECT last_seen_at FROM cardmarket_products WHERE id = ?", (first_id,)).fetchone()[0]
        self.assertEqual(last_seen, "2026-08-23T10:00:00+0200")


if __name__ == "__main__":
    unittest.main()
