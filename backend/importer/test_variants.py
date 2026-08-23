import unittest

from variants import classify_variant_group, group_products


class GroupProductsTest(unittest.TestCase):
    def test_groups_by_expansion_and_metacard(self):
        products = [
            {"idProduct": 1, "idExpansion": 5285, "idMetacard": 100, "name": "A"},
            {"idProduct": 2, "idExpansion": 5285, "idMetacard": 100, "name": "A (V.2)"},
            {"idProduct": 3, "idExpansion": 5285, "idMetacard": 200, "name": "B"},
        ]
        groups = group_products(products)
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(groups[(5285, 100)]), 2)
        self.assertEqual(len(groups[(5285, 200)]), 1)

    def test_missing_metacard_gets_own_group(self):
        products = [{"idProduct": 9, "idExpansion": 5285, "idMetacard": None, "name": "X"}]
        groups = group_products(products)
        self.assertEqual(groups[("no_metacard", 9)], products)


class ClassifyVariantGroupTest(unittest.TestCase):
    def test_single_product_group_is_normal(self):
        group = [{"idProduct": 1, "idExpansion": 5285, "idMetacard": 100, "name": "Gandalf the Grey"}]
        decisions = classify_variant_group(group, {})
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].printing_variant, "normal")
        self.assertEqual(decisions[0].classification_note, "single")

    def test_clear_trend_difference_suggests_parallel(self):
        group = [
            {"idProduct": 1, "idExpansion": 4976, "idMetacard": 100, "name": "Treasure Token"},
            {"idProduct": 2, "idExpansion": 4976, "idMetacard": 100, "name": "Treasure Token (V.4)"},
        ]
        price_entries = {1: {"trend": 1.0}, 2: {"trend": 5.0}}
        decisions = {d.id_product: d for d in classify_variant_group(group, price_entries)}
        self.assertEqual(decisions[2].printing_variant, "suggested_parallel")
        self.assertEqual(decisions[2].variant_label, "(V.4)")
        self.assertEqual(decisions[1].printing_variant, "normal")
        self.assertEqual(decisions[1].classification_note, "suggested")

    def test_similar_price_is_other(self):
        # ej. "Erg Raiders" de fase2 doc: precios practicamente iguales, sin sustento para elegir.
        group = [
            {"idProduct": 1, "idExpansion": 5285, "idMetacard": 200, "name": "Erg Raiders"},
            {"idProduct": 2, "idExpansion": 5285, "idMetacard": 200, "name": "Erg Raiders"},
        ]
        price_entries = {1: {"trend": 2.0}, 2: {"trend": 2.02}}
        decisions = classify_variant_group(group, price_entries)
        self.assertTrue(all(d.printing_variant == "other" for d in decisions))
        self.assertTrue(all(d.classification_note == "ambiguous_similar_price" for d in decisions))

    def test_missing_trend_is_other(self):
        group = [
            {"idProduct": 1, "idExpansion": 5285, "idMetacard": 300, "name": "A"},
            {"idProduct": 2, "idExpansion": 5285, "idMetacard": 300, "name": "B"},
        ]
        price_entries = {1: {"trend": 5.0}}  # falta el trend del idProduct 2
        decisions = classify_variant_group(group, price_entries)
        self.assertTrue(all(d.printing_variant == "other" for d in decisions))
        self.assertTrue(all(d.classification_note == "ambiguous_no_price" for d in decisions))


if __name__ == "__main__":
    unittest.main()
