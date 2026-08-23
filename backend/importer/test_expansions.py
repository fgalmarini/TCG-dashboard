import unittest

from expansions import get_or_create_expansion
from report import ImportReport
from test_support import make_test_db


class ExpansionsTest(unittest.TestCase):
    def setUp(self):
        self.conn = make_test_db()
        self.report = ImportReport()

    def tearDown(self):
        self.conn.close()

    def test_new_expansion_inserted_with_null_name(self):
        cache = {}
        expansion_id = get_or_create_expansion(self.conn, 3, 5285, cache, self.report, "magic")
        row = self.conn.execute("SELECT name FROM expansions WHERE id = ?", (expansion_id,)).fetchone()
        self.assertIsNone(row[0])
        self.assertIn(("magic", 5285), self.report.new_expansions)

    def test_second_call_reuses_cache_without_reinsert(self):
        cache = {}
        first = get_or_create_expansion(self.conn, 3, 5285, cache, self.report, "magic")
        second = get_or_create_expansion(self.conn, 3, 5285, cache, self.report, "magic")
        self.assertEqual(first, second)
        self.assertEqual(len(self.report.new_expansions), 1)
        count = self.conn.execute("SELECT COUNT(*) FROM expansions WHERE cardmarket_id_expansion = 5285").fetchone()[0]
        self.assertEqual(count, 1)

    def test_existing_row_not_reported_as_new(self):
        self.conn.execute("INSERT INTO expansions (game_id, cardmarket_id_expansion, name) VALUES (3, 5285, 'LTR')")
        cache = {}
        expansion_id = get_or_create_expansion(self.conn, 3, 5285, cache, self.report, "magic")
        row = self.conn.execute("SELECT name FROM expansions WHERE id = ?", (expansion_id,)).fetchone()
        self.assertEqual(row[0], "LTR")
        self.assertEqual(self.report.new_expansions, [])


if __name__ == "__main__":
    unittest.main()
