# POKEMON-151-002C — CARDMARKET FINISH SEMANTICS

Official semantic findings: see `01_cardmarket_semantics.md`.
Observed product-page behavior: see `03_product_page_evidence.csv` and `04_reverse_filter_analysis.csv`.
BASE metric conclusion: BASE reverse inclusion is not determined by local JSON or current sampled observations.
FOIL metric conclusion: FOIL is not equivalent to Pokémon reverse_holo without product-specific evidence.
Reverse Holo pricing conclusion: NO from the local Price Guide without reverse-specific evidence.
Higher-rarity conclusion: handled as separate groups; no finish/metric inference is forced.
Version conclusion: recorded per observed URL; V-number semantics are not assumed.

Canonical EXACT products: 137
Metric mappings reviewed: 270
Metric EXACT: 0
Metric SUPPORTED: 0
Metric AMBIGUOUS: 266
Metric UNRESOLVED: 4
Metric MISMATCH: 0
pricing_eligible: 0
prices applied: 0

Cardmarket FOIL != Pokémon Reverse Holo unless product-specific evidence proves otherwise.
Sample patterns never promote unobserved products to EXACT.
Apply requires `--offline`; no network request is made during apply.
