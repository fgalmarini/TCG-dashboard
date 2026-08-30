# One Piece pricing audit

## Scope and sources

- Total printings: **13684**

- Snapshot timestamp: **2026-08-29T13:00:00+00:00**

- Sources: `source_manifest.json`


## Matching

- Exact Cardmarket: **6**

- Ambiguous: **12530**

- Mismatch: **778**

- Missing: **369**

- Unpriced: **1**

- Current Cardmarket exact coverage: **0.04%**

- Current CardTrader-priced: **10962**

- Identity mismatches: **778**

- Currency mismatches: **0**


## Price comparison

- OK: **1**

- Review: **0**

- High: **2**

- Critical: **781**


## Causes

| Cause | Count | Percent | Collection impact |
| --- | --- | --- | --- |
| ambiguous_identity | 12530 | 91.57 | 0.0 |
| wrong_cardmarket_id | 778 | 5.69 | 0.0 |
| missing_cardmarket_id | 369 | 2.7 | 0.0 |
| missing_product | 1 | 0.01 | 0.0 |


## Collection

- Current total value: **€259.08**

- Comparable units: **0 / 23**

- Comparable coverage: **0.0%**

- Comparable current value: **€0.00**

- Comparable Cardmarket Trend value: **€0.00**

- Comparable difference: **€0.00**


## Verdict

- One Piece identity: **UNSAFE**

- One Piece pricing parity: **UNSAFE**



## EB02-061

Todos los productos se mantienen separados por `idProduct`; la Product Catalogue bulk no expone una versión V1/V2/V3 cuando no aparece en el nombre.

| local ID | local set | language | local version | current price | current source | current source product ID | Cardmarket idProduct | Cardmarket expansion | Cardmarket version | Low | Trend | AVG7 | match status | primary cause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 6420 | — | en | — | — | — | — | 808171 | 6018 | not exposed in bulk name | 1 | 1.55 | 1.72 | OUT_OF_SCOPE | — |
| 6420 | — | en | — | — | — | — | 808172 | 6018 | not exposed in bulk name | 28 | 44.59 | 45.11 | OUT_OF_SCOPE | — |
| 6420 | — | en | — | — | — | — | 808173 | 6018 | not exposed in bulk name | 2250 | 2687.64 | 2489.4 | OUT_OF_SCOPE | — |
| 6421 | — | en | — | — | — | — | 808171 | 6018 | not exposed in bulk name | 1 | 1.55 | 1.72 | OUT_OF_SCOPE | — |
| 6421 | — | en | — | — | — | — | 808172 | 6018 | not exposed in bulk name | 28 | 44.59 | 45.11 | OUT_OF_SCOPE | — |
| 6421 | — | en | — | — | — | — | 808173 | 6018 | not exposed in bulk name | 2250 | 2687.64 | 2489.4 | OUT_OF_SCOPE | — |
| 7164 | eb-02 | en | Secret Rare | 7.14 | cardtrader | 330430 | 823515 | 6028 | not exposed in bulk name | 2.5 | 5.1 | 3.8 | AMBIGUOUS | ambiguous_identity |
| 7165 | — | en | — | — | — | — | 823515 | 6028 | not exposed in bulk name | 2.5 | 5.1 | 3.8 | OUT_OF_SCOPE | — |
| 7165 | — | en | — | — | — | — | 823516 | 6028 | not exposed in bulk name | 40 | 89.75 | 86 | OUT_OF_SCOPE | — |
| 7165 | — | en | — | — | — | — | 823517 | 6028 | not exposed in bulk name | 2550 | 4649.99 | 4438.78 | OUT_OF_SCOPE | — |
| 7949 | — | en | — | — | — | — | 838704 | 6233 | not exposed in bulk name | 0.77 | 1.57 | 1.14 | OUT_OF_SCOPE | — |
| 7949 | — | en | — | — | — | — | 838705 | 6233 | not exposed in bulk name | 119 | 189.17 | 164.69 | OUT_OF_SCOPE | — |
| 7950 | — | en | — | — | — | — | 838704 | 6233 | not exposed in bulk name | 0.77 | 1.57 | 1.14 | OUT_OF_SCOPE | — |
| 7950 | — | en | — | — | — | — | 838705 | 6233 | not exposed in bulk name | 119 | 189.17 | 164.69 | OUT_OF_SCOPE | — |
| 8975 | — | en | — | — | — | — | 852319 | 6242 | not exposed in bulk name | 2 | 4.97 | 3.67 | OUT_OF_SCOPE | — |
| 8975 | — | en | — | — | — | — | 852320 | 6242 | not exposed in bulk name | 120 | 309.95 | 312.7 | OUT_OF_SCOPE | — |
| 8976 | — | en | — | — | — | — | 852319 | 6242 | not exposed in bulk name | 2 | 4.97 | 3.67 | OUT_OF_SCOPE | — |
| 8976 | — | en | — | — | — | — | 852320 | 6242 | not exposed in bulk name | 120 | 309.95 | 312.7 | OUT_OF_SCOPE | — |
| 21129 | eb-02 | jp | Secret Rare | 7.34 | cardtrader | 330430 | 823515 | 6028 | not exposed in bulk name | 2.5 | 5.1 | 3.8 | AMBIGUOUS | ambiguous_identity |
| 21132 | eb-02 | en | Manga Panel Alternate Art \| Secret Rare | 7000.64 | cardtrader | 330433 | 808173 | 6018 | not exposed in bulk name | 2250 | 2687.64 | 2489.4 | AMBIGUOUS | ambiguous_identity |
| 21132 | eb-02 | en | Manga Panel Alternate Art \| Secret Rare | 7000.64 | cardtrader | 330433 | 823517 | 6028 | not exposed in bulk name | 2550 | 4649.99 | 4438.78 | AMBIGUOUS | ambiguous_identity |
| 21133 | eb-02 | jp | Manga Panel Alternate Art \| Secret Rare | 2200.62 | cardtrader | 330433 | 808173 | 6018 | not exposed in bulk name | 2250 | 2687.64 | 2489.4 | AMBIGUOUS | ambiguous_identity |
| 21133 | eb-02 | jp | Manga Panel Alternate Art \| Secret Rare | 2200.62 | cardtrader | 330433 | 823517 | 6028 | not exposed in bulk name | 2550 | 4649.99 | 4438.78 | AMBIGUOUS | ambiguous_identity |
| 22576 | prb02 | en | Special Rare | 590.64 | cardtrader | 350886 | 838705 | 6233 | not exposed in bulk name | 119 | 189.17 | 164.69 | AMBIGUOUS | ambiguous_identity |
| 22576 | prb02 | en | Special Rare | 590.64 | cardtrader | 350886 | 852320 | 6242 | not exposed in bulk name | 120 | 309.95 | 312.7 | AMBIGUOUS | ambiguous_identity |
| 22577 | prb02 | jp | Special Rare | 500.64 | cardtrader | 350886 | 838705 | 6233 | not exposed in bulk name | 119 | 189.17 | 164.69 | AMBIGUOUS | ambiguous_identity |
| 22577 | prb02 | jp | Special Rare | 500.64 | cardtrader | 350886 | 852320 | 6242 | not exposed in bulk name | 120 | 309.95 | 312.7 | AMBIGUOUS | ambiguous_identity |
| 23041 | prb02 | en | Secret Rare \| Reprint | 6.14 | cardtrader | 352178 | 838704 | 6233 | not exposed in bulk name | 0.77 | 1.57 | 1.14 | AMBIGUOUS | ambiguous_identity |
| 23041 | prb02 | en | Secret Rare \| Reprint | 6.14 | cardtrader | 352178 | 852319 | 6242 | not exposed in bulk name | 2 | 4.97 | 3.67 | AMBIGUOUS | ambiguous_identity |
| 23042 | prb02 | jp | Secret Rare \| Reprint | 5.84 | cardtrader | 352178 | 838704 | 6233 | not exposed in bulk name | 0.77 | 1.57 | 1.14 | AMBIGUOUS | ambiguous_identity |
| 23042 | prb02 | jp | Secret Rare \| Reprint | 5.84 | cardtrader | 352178 | 852319 | 6242 | not exposed in bulk name | 2 | 4.97 | 3.67 | AMBIGUOUS | ambiguous_identity |



### Acceptance checks

- `EB02 JP V2 != PRB02 JP V2`: PASS por `idProduct` disjuntos ([808173, 823515, 823517] vs [838704, 838705, 852319, 852320]); V2 explícito: no.

- `EB02 JP V2 != EB02 EN V2`: NOT_PROVABLE; el bulk no demuestra alcance lingüístico/versiones V2 exactos.

- `EB02 JP V2 != EB02 V1/V3`: NOT_PROVABLE; V1/V2/V3 no están expuestos explícitamente en los snapshots usados.
