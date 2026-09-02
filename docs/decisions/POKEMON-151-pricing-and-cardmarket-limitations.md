# Pokémon 151 Pricing and Cardmarket Limitations

Status: Implemented  
Scope: Pokémon 151 foundation and pricing discovery through `POKEMON-151-004B`  
Date: 2026-09-02

## Decision

Cardmarket remains the primary European pricing source. For Pokémon 151,
Cardmarket Low for an exact physical printing is the only source allowed to
populate `current_price` and `market_value`.

TCGplayer is stored only as a secondary USD market reference. Its observations
use `provider=pokemon_tcg_api` and `market=tcgplayer`; TCGdex is a cross-check.
TCGplayer never replaces Cardmarket `current_price`/`market_value` and never
participates in Overview, Collection, Wishlist, Top Cards, valuation, P&L or ROI.

## Cardmarket limitation

The Pokémon 151 catalog contains 210 Cardmarket products: 137 canonical
`EXACT` mappings and 73 canonical `AMBIGUOUS` mappings. Zero Cardmarket metric
families are exact enough to assign prices safely to physical finishes, so
`pricing_eligible=0` remains the rule.

The 73 mappings are intentionally unresolved. They must not be guessed from
card name, TCGdex artwork alone, price similarity, `idMetacard` alone or an
external marketplace ID alone. The manual review workflow is prepared, but no
manual mapping has been promoted.

## Reason

The available Cardmarket Product Catalogue and Price Guide do not expose enough
deterministic identity/finish information to separate `normal`, `holo` and
`reverse_holo` at physical-printing price level. Public Cardmarket listing
access was investigated and is `BLOCKED` for stable automation. No scraper,
bypass or undocumented endpoint is used.

## Consequence

Do not guess. Keep the 73 mappings unresolved and keep exact physical
Cardmarket prices `NULL` where no safe finish mapping exists. Cardmarket
Trend/AVG metrics and TCGplayer values are not silent fallbacks.

The generic structures remain separated:

- `cardmarket_product_printing_scopes` maps a Cardmarket product to a canonical
  identity and independently records finish scope.
- `cardmarket_product_metric_mappings` audits metric-family-to-printing
  relationships and pricing eligibility; Pokémon 151 has zero eligible rows.
- `market_price_observations` stores source-neutral provider, market, metric,
  currency and historical snapshot observations without becoming primary price.

The catalog hierarchy is:

```text
Canonical Card Identity
        ↓
Physical Printing / Finish
        ↓
External Marketplace Identity
        ↓
Market Price Observation
```

Rarity, finish, treatment, marketplace product and observation remain distinct
concepts.

## Future reconsideration

This decision may be revisited if deterministic Cardmarket-specific evidence,
stable listing-level evidence, a trustworthy source or manually verified
identity/finish evidence becomes available. Any reconsideration must preserve
the primary Cardmarket policy and the no-silent-fallback rule.
