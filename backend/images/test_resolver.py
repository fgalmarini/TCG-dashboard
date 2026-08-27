import unittest

from .resolver import resolve_scryfall_card, resolve_scryfall_raw, validate_remote_image_url


class ResolverTest(unittest.TestCase):
    def test_root_image_uris_resolve_exact(self):
        resolution = resolve_scryfall_card(
            {
                "id": "sf-root",
                "lang": "en",
                "image_uris": {
                    "small": "https://cards.scryfall.io/small/front/a/b/sf-root.jpg",
                    "large": "https://cards.scryfall.io/large/front/a/b/sf-root.jpg",
                },
            }
        )

        self.assertEqual(resolution.status, "resolved")
        self.assertEqual(resolution.match_quality, "exact")
        self.assertEqual(len(resolution.faces), 1)
        self.assertEqual(resolution.faces[0].face_index, 0)
        self.assertEqual(resolution.faces[0].small_url, "https://cards.scryfall.io/small/front/a/b/sf-root.jpg")
        self.assertEqual(resolution.faces[0].large_url, "https://cards.scryfall.io/large/front/a/b/sf-root.jpg")

    def test_multi_face_image_uris_resolve_each_face(self):
        resolution = resolve_scryfall_card(
            {
                "id": "sf-faces",
                "lang": "en",
                "card_faces": [
                    {"image_uris": {"small": "https://cards.scryfall.io/small/front/a/b/front.jpg"}},
                    {"image_uris": {"normal": "https://cards.scryfall.io/normal/back/a/b/back.jpg"}},
                ],
            }
        )

        self.assertEqual(resolution.status, "resolved")
        self.assertEqual([face.face_index for face in resolution.faces], [0, 1])
        self.assertEqual(resolution.faces[1].large_url, "https://cards.scryfall.io/normal/back/a/b/back.jpg")

    def test_missing_image_returns_missing_without_exception(self):
        resolution = resolve_scryfall_card({"id": "sf-missing", "lang": "en"})
        self.assertEqual(resolution.status, "missing")
        self.assertEqual(resolution.faces, [])

    def test_ambiguous_payload_without_source_card_id_does_not_assign_art(self):
        resolution = resolve_scryfall_card(
            {"image_uris": {"small": "https://cards.scryfall.io/small/front/a/b/unsafe.jpg"}}
        )
        self.assertEqual(resolution.status, "ambiguous")
        self.assertEqual(resolution.faces, [])

    def test_invalid_raw_returns_error(self):
        resolution = resolve_scryfall_raw("{not-json")
        self.assertEqual(resolution.status, "error")

    def test_url_validation_rejects_unsafe_urls(self):
        unsafe = [
            "http://cards.scryfall.io/small/front/a/b/card.jpg",
            "javascript:alert(1)",
            "https://localhost/small/front/a/b/card.jpg",
            "https://127.0.0.1/small/front/a/b/card.jpg",
            "https://example.com/small/front/a/b/card.jpg",
            "data:image/png;base64,AAAA",
        ]
        for url in unsafe:
            with self.subTest(url=url):
                self.assertIsNone(validate_remote_image_url(url))

    def test_url_validation_accepts_scryfall_https_image_host(self):
        url = "https://cards.scryfall.io/small/front/a/b/card.jpg"
        self.assertEqual(validate_remote_image_url(url), url)


if __name__ == "__main__":
    unittest.main()
