# Pokémon 151 schema audit

- `canonical_cards` stores one numbered identity per `game + set + collector_number`.
- `cards` stores physical printings and keeps finish separate from rarity and treatment.
- Pokémon finishes use generic `normal`, `holo`, and `reverse_holo`; Magic finishes remain unchanged.
- `card_images` stores exact-number `tcgdex` assets; no name/artwork fallback is used.
- Cardmarket expansion 5328 is preserved only as set-level external identity.
- No Pokémon product mapping, pricing resolution, price history, holding, or purchase price is imported.
- Schema support: cards finish variants=True; tcgdex images=True; mode=dry-run.
- Schema change is generic and additive; no Pokémon-only table or column was introduced.
