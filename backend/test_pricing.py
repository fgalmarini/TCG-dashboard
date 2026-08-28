import unittest

from pricing import resolve_cardtrader_marketplace


def offer(seller: int, cents: int, language: str = "en", **extra) -> dict:
    value = {
        "user": {"id": seller},
        "on_vacation": False,
        "graded": False,
        "price": {"cents": cents, "currency": "EUR"},
        "properties_hash": {
            "condition": "Near Mint",
            "onepiece_language": language,
            "signed": False,
            "altered": False,
        },
    }
    value.update(extra)
    return value


class CardTraderPricingTest(unittest.TestCase):
    def test_uses_five_cheapest_distinct_sellers(self):
        offers = [offer(1, 100), offer(1, 90), offer(2, 110), offer(3, 120),
                  offer(4, 130), offer(5, 140), offer(6, 1_000)]
        result = resolve_cardtrader_marketplace(offers, "en")
        self.assertEqual(result.current_price, 1.2)
        self.assertEqual(result.lowest_price, 0.9)
        self.assertEqual(result.sample_size, 5)
        self.assertEqual(result.confidence, "high")

    def test_rejects_wrong_language_or_ineligible_offer(self):
        offers = [
            offer(1, 10, language="jp"),
            offer(2, 20, on_vacation=True),
            offer(3, 30, graded=True),
            offer(4, 40, bundle_size=2),
            offer(5, 50, properties_hash={"condition": "Played", "onepiece_language": "en"}),
        ]
        result = resolve_cardtrader_marketplace(offers, "en")
        self.assertIsNone(result.current_price)
        self.assertEqual(result.sample_size, 0)

    def test_small_markets_keep_low_confidence_price(self):
        result = resolve_cardtrader_marketplace([offer(1, 100), offer(2, 200)], "en")
        self.assertEqual(result.current_price, 1.5)
        self.assertEqual(result.confidence, "low")


if __name__ == "__main__":
    unittest.main()
