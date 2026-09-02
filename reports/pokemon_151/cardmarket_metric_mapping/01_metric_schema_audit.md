# Pokémon 151 Metric → Finish schema audit

- Mode: `apply`
- `cardmarket_product_printing_scopes` remains the canonical product-level scope relation.
- `cardmarket_product_metric_mappings` is the generic per-product/per-metric-family relation because the canonical scope has one row per product.
- Base source columns: `['low', 'trend', 'avg1', 'avg7', 'avg30']`
- Foil source columns: `['low-holo', 'trend-holo', 'avg1-holo', 'avg7-holo', 'avg30-holo']`
- Observed expected columns: `['avg1', 'avg1-holo', 'avg30', 'avg30-holo', 'avg7', 'avg7-holo', 'low', 'low-holo', 'trend', 'trend-holo']`
- Unexpected metric-like columns: `['avg', 'avg-holo']`
- Numeric metric values are not persisted by this sprint.
- `pricing_eligible` is independent from both canonical and metric mapping status.
- No API/UI behavior or pricing workflow is changed.
