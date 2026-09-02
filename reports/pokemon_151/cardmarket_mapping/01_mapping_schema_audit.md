# Pokémon 151 Cardmarket mapping schema audit

- `cardmarket_products` is source inventory: it has Cardmarket fields but no direct card foreign key.
- `cardmarket_product_mappings` is the existing authoritative physical mapping table.
- The current mapping table cannot express canonical-only scope, multiple finishes, or `pricing_eligible`.
- A generic `cardmarket_product_printing_scopes` relation is therefore required and stores product, canonical, nullable physical card, finish scope, status, provenance and pricing eligibility.
- Only `EXACT` rows are persisted there; all persisted rows have `pricing_eligible=0` in this sprint.
- No Pokémon-only table was introduced; no API/UI/pricing behavior is changed.
- Mode: `apply`
