# POKEMON 151 CARDMARKET DISCOVERY

## Scope and source files

- Products: `/Users/facundogalmarini/Desktop/products_singles_6 (1).json` (SHA-256 `318cdf83b38813443530bb4d14f770ed0c1225be9ad87ddebbbee00b097613b5`).
- Price Guide: `/Users/facundogalmarini/Desktop/price_guide_6 (1).json` (SHA-256 `86282c2015adc332db82ce65d162f6cc44dc0bb3208b8bfedd952268ffafa145`).
- Scope is limited to the automatically selected source group below; no DB, catalog, pricing or existing TCG data was written.

## Required answers

1. **Exact Cardmarket expansion:** source evidence selects `idExpansion=5328` as the **151** base-set candidate. Cardmarket's public expansion path is `/en/Pokemon/Expansions/151`; the supplied JSON has no `expansion_name` or set-code field, so `MEW` remains a scoped candidate rather than a source value. The raw source expansion name remains `NULL`; related `Pokémon Card 151: Additionals`, Japanese and promo groups are not merged.
2. **Cardmarket single products:** `210`.
3. **Unique normalized collector numbers:** `0 available from these files`; `167` source `(idMetacard, normalized_card_name)` groups were observed instead.
4. **Expected 001–207 cards:** **NOT DETERMINABLE FROM CARDMARKET**; no collector number exists in either input. The selected source group has 210 Product IDs, which cannot be equated to 207 cards.
5. **Missing or duplicated numbers:** **NOT DETERMINABLE FROM CARDMARKET**; there are no observed collector-number values to compare.
6. **Multiple-product collector numbers:** collector-number count is **NOT DETERMINABLE**; as a source-group proxy, `133` groups have exactly 1 Product ID, `34` groups have >1, and the maximum is `4` Product IDs. These are `(idMetacard, normalized_card_name)` groups, not collector numbers.
7. **Normal/reverse holo via separate Product IDs:** **NOT CONFIRMED**. Multiplicity exists, but no finish field or explicit reverse-holo marker exists. Whether normal and reverse share a Product ID is also **NOT DETERMINABLE**.
8. **Holo separately:** **NOT CONFIRMED** at product identity level. The Price Guide has `*-holo` metrics, but that is not evidence that the Product Catalogue rows are separate holo products. Which numbered cards have or lack reverse holo is **NOT DETERMINABLE** because neither numbers nor finish are present.
9. **Observed variant/finish vocabulary:** source product names expose card names and attack/rules text only; no `normal`, `holo`, `reverse holo`, `Illustration Rare`, `Ultra Rare`, `Special Illustration Rare`, `Hyper Rare` or stamped field was observed.
10. **Rarity vs finish dimensions:** **NOT DETERMINABLE FROM CARDMARKET**; neither dimension is present in the product records. The audit does not reinterpret `ex` as rarity.
11. **Illustration Rare / Ultra Rare / Special Illustration Rare / Hyper Rare:** **NOT DETERMINABLE FROM CARDMARKET**; no rarity or collector number fields.
12. **Promos or stamped cards associated with this expansion:** no explicit promo/stamped marker was found in the selected product names; absence is not proof of absence from Cardmarket's broader product model.
13. **Language:** **NOT PRESENT IN THESE FILES**; language is neither product-level nor listing/offer-level data here.
14. **Exact Price Guide joins:** `210` one-to-one joins; `210` products have any idProduct match including duplicates; `0` are missing.
15. **Products with Low:** `210`.
16. **Trend / AVG1 / AVG7 / AVG30:** `210 / 210 / 210 / 210`.
17. **Products not safely mappable to a logical numbered card:** all scoped products are unresolved for official numbering/printing identity because those fields are absent; see `06_unresolved_products.csv`.
18. **Is collector_number sufficient as printing identity?** No conclusion can be tested from this source cut; even if added later, the observed Product ID multiplicity shows it should not be assumed sufficient without finish/variant/language evidence.
19. **Logical-card identity for TCG DASHBOARD:** reuse the neutral canonical-card concept, but require an externally evidenced Pokémon card number/name mapping; do not use name alone.
20. **Printing/variant identity:** use the existing printing identity concept plus Cardmarket Product ID, expansion identity, language when evidenced, and an explicit finish/treatment/variant field only when supported.
21. **Cardmarket external identifiers:** store `idProduct` as the product external ID and `idExpansion` as the expansion external ID; retain `idMetacard` as source metadata/grouping evidence, not as the sole printing key.
22. **Initial-plan assumptions:** confirmed: Cardmarket product catalog and Price Guide are separate files, products are Pokémon Single/category 51, and Product ID is the join key. Disproven/unavailable: the files do not expose expansion name, set code, collector number, rarity, language or finish, so 207-card and variant hypotheses cannot be confirmed from this source cut.

## Price policy guardrails

- `Low` is reported separately from `Trend` and AVG metrics.
- No fallback, historical price, CardTrader price or current-price update was applied.
- Price Guide source currency and available-item counts are not fields in these inputs; they remain NULL/unavailable.
- Duplicate `idProduct` price-guide entries are flagged and their normalized metrics are left NULL.

## Official numbering audit

- Observed collector-number values: **none; field NOT AVAILABLE**.
- Minimum, maximum, unique count, missing numbers, duplicate numbers, non-numeric formats and special formats: **NOT DETERMINABLE FROM CARDMARKET**.
- The `001–165`, `166–181`, `182–197`, `198–204`, `205–207` hypothesis cannot be confirmed or contradicted from these JSON files.
- The selected group has 210 Product IDs and 167 source metacard/name groups; neither count is an official card-number count.

## Key architecture conclusion

The supplied Cardmarket snapshots are adequate to preserve Product ID, expansion ID, category, name, metacard grouping and independent price metrics. They are not adequate to build a Pokémon printing catalog without an additional validated metadata source or a controlled manual mapping step. The current multi-TCG model can be reused, but no Pokémon import should infer collector numbers, language or finishes from names or `idMetacard` alone.

## Recommended next sprint

**POKEMON-151-001 — Catalog Data Model & Import**

Before implementation, define and validate the metadata source/contract for collector numbers, rarity, language and finish; preserve Cardmarket Product IDs and unresolved mappings; then design an additive dry-run import. Do not proceed automatically from this audit.

## Recommended model (discovery only; not implemented)

- **Logical Card:** canonical Pokémon card identity based on validated set + official collector number + card name.
- **Printing / Variant:** physical printing row with Cardmarket Product ID, expansion, language, finish/treatment/variant and validated rarity where available.
- **Cardmarket External Identity:** `idProduct` for product; `idExpansion` for expansion; `idMetacard` retained as non-authoritative source metadata.
- **Finish representation:** explicit nullable field; never infer normal/holo/reverse holo from missing data or from `*-holo` price metrics.
- **Rarity representation:** explicit nullable source-backed field, separate from finish.
- **Language representation:** explicit printing/listing scope only after source evidence; do not create language variants from these files.
- **Suggested natural uniqueness:** validated canonical card + release + language + finish/treatment/variant, with Cardmarket Product ID as provider identity; exact constraint remains to be designed in POKEMON-151-001.
- **Pokémon-specific metadata:** official set code, Pokédex/collector-number conventions, Pokémon rarity vocabulary and any language/set-specific variant rules.
- **Reusable model:** existing `games`, `sets`/releases, canonical cards, printings (`cards`), external-ID tables, nullable pricing and immutable price history.

## Selected source evidence

- `idExpansion=5328`: `210` products, `167` source metacard/name groups.
- Product-name rows containing the literal `151`: `3` distinct examples: Bulbasaur [Leech Seed | 151]; Ivysaur [Leech Seed | Vine Whip | 151]; Poliwag [Bubble | 151].
- Related candidate groups were not merged: top alternatives include `6099, 5402, 6311, 6168, 5525`.

**DB modified: NO. Existing Magic/One Piece modified: NO.**
