# Recommended pricing policy

Recommendation: `OPTION C`

1. Cardmarket remains the EUR primary source only when an exact physical finish and attributable metric are directly demonstrated.
2. Pokémon TCG API `reverseHolo*` is classified as `CARDMARKET_DERIVED_EXTERNAL`, with provenance `source=pokemon_tcg_api; underlying_market=cardmarket`; it is not imported or enabled automatically in this sprint.
3. TCGplayer normal/holofoil/reverseHolofoil remains a USD `secondary_market_reference`; it cannot overwrite or populate Cardmarket `current_price`.
4. A missing or blocked exact-finish source remains `NULL`.

Observed Route 1 status: `BLOCKED`. Observed API reverse low coverage: `149/207` numbered identities. Physical coverage recommendation counts: `{'tcgplayer_secondary_reference': 201, 'cardmarket_derived_external_reverse_low': 142, 'NULL': 19}`; by finish: `{'normal': {'tcgplayer_secondary_reference': 123, 'NULL': 5}, 'holo': {'tcgplayer_secondary_reference': 72, 'NULL': 9}, 'reverse_holo': {'tcgplayer_secondary_reference': 6, 'cardmarket_derived_external_reverse_low': 142, 'NULL': 5}}`.

This is a recommendation only. No pricing path was integrated and no database row was written.
