# Cardmarket semantics — Pokémon 151

Mode: `apply-offline`

Each conclusion is labelled as SOURCE FACT, OBSERVED BEHAVIOR, DERIVED CONCLUSION or UNKNOWN. Legacy PriceGuide documentation is never sufficient by itself for EXACT.

- **product** (`product`): Cardmarket product is the catalog identity identified by idProduct. — `UNKNOWN`. Source: https://api.cardmarket.com/ws/documentation/API_2.0%3AEntities%3AArticle [LEGACY_GONE]
- **article/listing** (`article/listing`): Article records may carry listing-specific flags and condition/language. — `UNKNOWN`. Source: https://api.cardmarket.com/ws/documentation/API_2.0%3AEntities%3AArticle [LEGACY_GONE]
- **isFoil** (`article/listing`): isFoil is a separate article property; the current Article documentation marks it deprecated for Pokémon singles. — `UNKNOWN`. Source: https://api.cardmarket.com/ws/documentation/API_2.0%3AEntities%3AArticle [LEGACY_GONE]
- **isReverseHolo** (`article/listing`): isReverseHolo is a separate Pokémon article property. — `UNKNOWN`. Source: https://api.cardmarket.com/ws/documentation/API_2.0%3AEntities%3AArticle [LEGACY_GONE]
- **Reverse Holo** (`listing attribute`): Reverse Holo is a Pokémon listing attribute, not a rarity. — `SOURCE FACT`. Source: https://help.cardmarket.com/en/finding-and-listing-pokemon-cards [OK]
- **Regular Holofoil** (`card characteristic/rarity`): Regular Holofoil is distinguished from Reverse Holo in Pokémon listings. — `SOURCE FACT`. Source: https://help.cardmarket.com/en/finding-and-listing-pokemon-cards [OK]
- **version** (`product/catalog`): Cardmarket documents versions as potentially distinct and warns against assuming same-name products are interchangeable. — `SOURCE FACT`. Source: https://help.cardmarket.com/en/finding-and-listing-pokemon-cards [OK]
- **idProduct** (`product`): External Cardmarket product identifier. — `UNKNOWN`. Source: https://api.cardmarket.com/ws/documentation/API_2.0%3AEntities%3AArticle [LEGACY_GONE]
- **idMetacard** (`metaproduct/group`): Existing 002 evidence treats idMetacard as a commercial grouping, not numbered-card identity. — `DERIVED CONCLUSION`. Source: local Price Guide JSON [LOCAL]
- **base Price Guide metric** (`price-guide`): Local JSON exposes ['low', 'trend', 'avg1', 'avg7', 'avg30']. — `SOURCE FACT`. Source: local Price Guide JSON [LOCAL]
- **foil Price Guide metric** (`price-guide`): Local JSON exposes ['low-holo', 'trend-holo', 'avg1-holo', 'avg7-holo', 'avg30-holo']. — `SOURCE FACT`. Source: local Price Guide JSON [LOCAL]
- **legacy PriceGuide API** (`documentation`): Legacy PriceGuide documentation is historical evidence only and must not be the sole basis for EXACT. — `UNKNOWN`. Source: https://api.cardmarket.com/ws/documentation/API_2.0%3APriceGuide [LEGACY_GONE]

Cardmarket FOIL is not mapped to Pokémon reverse_holo without product-specific exclusive evidence.
