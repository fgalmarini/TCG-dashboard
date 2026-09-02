# Cardmarket Pokémon 151 — Source Schema Audit

## Scope and provenance

- Products source: `/Users/facundogalmarini/Desktop/products_singles_6 (1).json`
- Products SHA-256: `318cdf83b38813443530bb4d14f770ed0c1225be9ad87ddebbbee00b097613b5`
- Price Guide source: `/Users/facundogalmarini/Desktop/price_guide_6 (1).json`
- Price Guide SHA-256: `86282c2015adc332db82ce65d162f6cc44dc0bb3208b8bfedd952268ffafa145`
- Products top-level keys: `version, createdAt, products`
- Price Guide top-level keys: `version, createdAt, priceGuides`
- Products records: `73194`; Price Guide records: `78225`
- The command did not open or modify SQLite; it has no network dependency.

## Actual record fields

### `products_singles`

| field | present | non-NULL | NULL | types | sample values |
| --- | --- | --- | --- | --- | --- |
| idProduct | 73194 | 73194 | 0 | number | 273532; 273533; 273534 |
| name | 73194 | 73194 | 0 | string | Weedle [Multiply]; Kakuna [Bug Bite \| Primal Clash]; Beedrill [Allergic Shock \| Twineedle] |
| idCategory | 73194 | 73194 | 0 | number | 51 |
| categoryName | 73194 | 73194 | 0 | string | Pokémon Single |
| idExpansion | 73194 | 73194 | 0 | number | 1585; 1523; 1525 |
| idMetacard | 73194 | 73194 | 0 | number | 340471; 340472; 340473 |
| dateAdded | 73194 | 73194 | 0 | string | 0000-00-00 00:00:00; 2015-05-20 14:04:29; 2015-05-20 14:05:22 |

### `price_guide`

| field | present | non-NULL | NULL | types | sample values |
| --- | --- | --- | --- | --- | --- |
| idProduct | 78225 | 78225 | 0 | number | 271439; 271440; 271823 |
| idCategory | 78225 | 78225 | 0 | number | 52; 53; 51 |
| avg | 78222 | 63544 | 14681 | number | 99.99; 2103; 463.26 |
| low | 78222 | 71419 | 6806 | number | 85; 3600; 250 |
| trend | 78222 | 68954 | 9271 | number | 344.42; 2239.24; 582.01 |
| avg1 | 78222 | 61854 | 16371 | number | 0.35; 0.05; 0.89 |
| avg7 | 78222 | 61854 | 16371 | number | 0.16; 0.18; 0.4 |
| avg30 | 78222 | 61850 | 16375 | number | 0.16; 0.22; 0.61 |
| avg-holo | 68964 | 19386 | 58839 | number | 0.2; 1.03; 0.95 |
| low-holo | 68964 | 24015 | 54210 | number | 0.1; 0.05; 0.6 |
| trend-holo | 68964 | 67962 | 10263 | number | 3.93; 178.28; 90.03 |
| avg1-holo | 68964 | 28479 | 49746 | number | 0.2; 0.45; 1 |
| avg7-holo | 68964 | 28479 | 49746 | number | 0.47; 0.86; 1.55 |
| avg30-holo | 68964 | 28479 | 49746 | number | 0.58; 0.49; 1.83 |

## Requested-field availability

| requested concept | products source | price source | audit treatment |
| --- | --- | --- | --- |
| Cardmarket product ID | SOURCE FIELD: idProduct | SOURCE FIELD: idProduct | copied and used for strict join |
| Product name | SOURCE FIELD: name | NOT AVAILABLE | copied; final bracket removed only for derived display name |
| Expansion ID | SOURCE FIELD: idExpansion | NOT AVAILABLE | used for scope filtering |
| Expansion name / set code | NOT AVAILABLE | NOT AVAILABLE | NULL; no expansion name or code exists in these snapshots |
| Category / game | SOURCE FIELD: categoryName/idCategory | SOURCE FIELD: idCategory | copied; all scoped products are Pokémon Single/category 51 |
| Metacard identity | SOURCE FIELD: idMetacard | NOT AVAILABLE | retained as source grouping evidence, not official identity |
| Collector number | NOT AVAILABLE | NOT AVAILABLE | NULL; numbering hypotheses are not determinable |
| Rarity | NOT AVAILABLE | NOT AVAILABLE | NULL; `ex` in name is not treated as rarity |
| Version / finish / variant | NOT AVAILABLE | NOT AVAILABLE | NULL; no variant is forced |
| Language | NOT AVAILABLE | NOT AVAILABLE | NULL; cannot create language variants |
| URL / slug | NOT AVAILABLE | NOT AVAILABLE | no URL-like field observed |
| Low / Trend / AVG1 / AVG7 / AVG30 | NOT AVAILABLE | SOURCE FIELDS | strict idProduct join; duplicate joins are not normalized |
| Holo price metrics | NOT AVAILABLE | SOURCE FIELDS: *-holo | captured separately; not interpreted as a product finish |
| Available item count / source currency | NOT AVAILABLE | NOT AVAILABLE | NULL; not present in these files |

## Source-derived expansion candidate selection

Selected `idExpansion`: **5328**.
Selection method: `auto_selected_by_source_fingerprint; highest anchor-name score, target-marker evidence, near-207 product-count evidence and no-code-card evidence; not a hardcoded Product ID`.
The selected group is the highest-evidence source group, not a hardcoded Product ID mapping.
The public Cardmarket expansion name/set code are not fields in the supplied JSON; the report therefore separates source facts from the scoped Cardmarket label.

| idExpansion | products | unique metacards | unique names | anchors | 151 markers | code cards | score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 5328 | 210 | 167 | 167 | 9 | 5 | 0 | 9317 |
| 6099 | 192 | 151 | 151 | 9 | 3 | 0 | 9265 |
| 5402 | 242 | 175 | 175 | 9 | 10 | 8 | 9065 |
| 6311 | 202 | 187 | 187 | 8 | 2 | 0 | 8255 |
| 6168 | 141 | 80 | 80 | 8 | 2 | 0 | 8194 |
| 5525 | 52 | 48 | 48 | 6 | 3 | 0 | 6125 |
| 6219 | 306 | 153 | 153 | 5 | 6 | 0 | 5241 |
| 6127 | 302 | 256 | 256 | 4 | 6 | 0 | 4245 |
| 5802 | 209 | 155 | 155 | 4 | 1 | 10 | 3838 |
| 6128 | 211 | 196 | 196 | 3 | 4 | 0 | 3296 |
| 6328 | 358 | 325 | 325 | 3 | 5 | 0 | 3169 |
| 5960 | 45 | 42 | 42 | 3 | 0 | 0 | 3058 |
| 5241 | 304 | 210 | 210 | 2 | 2 | 0 | 2163 |
| 6442 | 97 | 70 | 70 | 2 | 0 | 0 | 2110 |
| 5519 | 360 | 191 | 191 | 2 | 0 | 0 | 2067 |

Candidate selection anchors are exact source product names from the 151 card fingerprint. They validate the source group composition, but do not provide collector numbers, rarity, finish or language.
