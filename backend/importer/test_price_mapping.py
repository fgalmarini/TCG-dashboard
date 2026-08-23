import unittest

from price_mapping import map_price_guide_entry


class PriceMappingTest(unittest.TestCase):
    def test_both_base_and_alt_present(self):
        entry = {
            "idProduct": 1, "idCategory": 1,
            "avg": 0.31, "low": 0.03, "trend": 0.31, "avg1": 0.26, "avg7": 0.39, "avg30": 0.34,
            "avg-foil": 0.61, "low-foil": 0.2, "trend-foil": 0.79, "avg1-foil": 1, "avg7-foil": 0.65, "avg30-foil": 0.7,
        }
        result = map_price_guide_entry(entry, "-foil")
        self.assertEqual(result["avg"], 0.31)
        self.assertEqual(result["avg_alt"], 0.61)
        self.assertEqual(result["trend_alt"], 0.79)

    def test_alt_keys_absent(self):
        # 2839 casos reales en Magic: sin ninguna key -foil.
        entry = {"idProduct": 1, "idCategory": 1, "avg": 0.31, "low": 0.03, "trend": 0.31, "avg1": 0.26, "avg7": 0.39, "avg30": 0.34}
        result = map_price_guide_entry(entry, "-foil")
        self.assertEqual(result["avg"], 0.31)
        self.assertIsNone(result["avg_alt"])
        self.assertIsNone(result["low_alt"])

    def test_alt_key_present_but_null(self):
        # caso real de Pokemon: "avg-holo": null
        entry = {
            "idProduct": 1, "idCategory": 51,
            "avg": 0.13, "low": 0.02, "trend": 0.16, "avg1": 0.33, "avg7": 0.18, "avg30": 0.14,
            "avg-holo": None, "low-holo": 0.1, "trend-holo": 0.65, "avg1-holo": 0.2, "avg7-holo": 0.47, "avg30-holo": 0.58,
        }
        result = map_price_guide_entry(entry, "-holo")
        self.assertIsNone(result["avg_alt"])
        self.assertEqual(result["low_alt"], 0.1)

    def test_base_keys_absent_only_alt_present(self):
        # 21 casos reales en Magic: solo keys -foil, sin base.
        entry = {"idProduct": 1, "idCategory": 1, "avg-foil": 0.5, "low-foil": 0.1, "trend-foil": 0.4, "avg1-foil": 0.3, "avg7-foil": 0.2, "avg30-foil": 0.6}
        result = map_price_guide_entry(entry, "-foil")
        self.assertIsNone(result["avg"])
        self.assertEqual(result["avg_alt"], 0.5)


if __name__ == "__main__":
    unittest.main()
