import unittest

from .scryfall.client import ScryfallClient


class ScryfallClientTest(unittest.TestCase):
    def test_exact_set_number_request_can_pin_language(self):
        request=ScryfallClient().card_by_set_number_request("HOB", "265", "EN")
        self.assertEqual(request.full_url,"https://api.scryfall.com/cards/hob/265/en")
        self.assertEqual(request.get_header("User-agent"),"TCG-Dashboard/1.0")
