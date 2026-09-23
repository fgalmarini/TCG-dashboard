# HOB-PREFLIGHT-001 — The Hobbit canonical scope

Run date: 2026-09-22. Database writes: **0**.

## Scope method

Scryfall API set searches for `hob`, `hoc`, and `thob`, with `unique=prints`, `include_extras=true`, and `include_variations=true`. Included only English (`lang=en`), paper (`paper` in `games`), non-digital records. A physical identity is `set + collector_number + language + finish`; treatment remains a separate dimension. `physical_scope.csv` has one row per physical identity/finish. `identities.csv` has the source identity and all finishes reported by Scryfall.

No LTR/LTC record contributed to construction of the Hobbit catalog. They were read only in the final regression query.

## Confirmed scope counts

| Set | English physical source records / collector numbers | Nonfoil identities | Foil identities | Expanded identity/finish rows |
|---|---:|---:|---:|---:|
| HOB | 321 | 280 | 321 | 601 |
| HOC | 153 | 113 | 92 | 205 |
| THOB | 15 | 15 | 13 | 28 |
| **Total** | **489** | **408** | **426** | **834** |

`foil` is Scryfall’s finish key. `finish_detail` distinguishes surge foil when the source record marks `promo_types=surgefoil`; remaining foil rows are identified as traditional or technology-unspecified. Headliner/gold and card frame styles are treatments, not finishes.

### HOC language exclusion

Five HOC records are Dwarvish-only and excluded from the English catalog: collector numbers 93–97 (Dwarven Warriors, The Reaver Cleaver, Arcane Signet, Mox Amber, Treasure Vault). Scryfall uses `lang=dw`; see `excluded_hoc_dwarvish.csv`.

## Cardmarket Extras and Art Series reconciliation

Cardmarket classifies the product type by the `Art Series:` prefix: those are separate art-card objects, even when the title matches a playable HOB card. HOB game-card listings with version suffixes resolve to the existing HOB collector identity/treatment and never form new XHOB playable printings. The rule and observed examples are listed in `cardmarket_extras_reconciliation.csv`. The complete dynamically rendered Cardmarket product-ID crosswalk is still unavailable (HTTP 403), and exact Cardmarket V.n to gold-stamped/standard mapping is not inferred. Public TCGplayer product records resolve the token pairings Cardmarket’s visible 12-name list does not distinguish.

### THOB tokens

THOB source records provide 13 English full-art token faces (Bird Soldier, Human Soldier, two Goblin Army artworks, Dragon, Dwarf, Bear, Elf, Wolf, Axe, Stone Boulder, two Treasure artworks) plus two helper cards (Enduring Story and On an Adventure). The 13 token faces each have nonfoil and traditional foil, and the two helpers are nonfoil only, yielding 28 face/finish rows.

The physical product is a double-sided token. Fourteen physical double-sided pairings are listed in `thob_physical_products.csv`, including two collector-number pairings absent from Cardmarket’s 12 visible product names (#2//13 and #8//6). The product catalog reports nine token/token pairings in both finishes, two foil-only pairings, and three nonfoil-only helper-containing pairings: 23 product/finish rows. The pair #15//14 orientation is recorded as numbered by the product catalog. Cardmarket’s title list is therefore insufficient as a complete pairing census; product-level catalog cross-checks are required.

## Regression (read-only SQLite)

- LTR active main printings excluding active Art Series: **1,544**.
- LTC active printings: **761**.
- Additional local rows: LTR has 45 active Art Series rows plus 640 legacy rows; LTC has 1 legacy row. Thus raw all-row counts are not the requested active printing baseline.
- Collection: 125 rows / 128 quantity.
- Wishlist: 39 rows / 39 quantity.
- Pricing state captured: 977 `market_price_history`, 1,676 `market_price_observations`, 38,780 `printing_price_resolutions`, 13,171 Cardmarket mappings.
- Hobbit rows in DB: **0**.
- No DB writes were made. Collection, Wishlist and pricing were queried read-only for baseline; no mutations were run.

## Files

- `physical_scope.csv`: expanded HOB/HOC/THOB rows by finish.
- `identities.csv`: source records with all source-supported finish options.
- `excluded_hoc_dwarvish.csv`: the five explicitly excluded HOC cards.
- `summary.json`: source acquisition, aggregates and regression counts.
- `cardmarket_extras_reconciliation.csv`: Extras classification and duplicate policy.

## Source refinement (2026-09-22 continuation)

- Wizards' official Hobbit Tokens article confirms **13 full-art tokens + 2 helper cards** in Play Boosters. The 13 token designs are available as nonfoil double-sided tokens in Play Boosters and traditional-foil double-sided tokens in Collector Boosters. Helpers do not appear in Collector Boosters. Thus THOB Scryfall’s 15 face records expand to 13 token faces × 2 finishes plus 2 nonfoil helpers = **28 face/finish rows**. `thob_physical_products.csv` reconciles 14 double-sided pair designs expand to 23 observed product/finish rows. The earlier 12-product Cardmarket count omitted product-level distinctions; TCGplayer records #2//13 and #8//6 in addition to its visible 12-name list.
- Wizards' official Art Cards article confirms 54 numbered art cards with both unstamped and gold-stamped copies (gold stamp is a treatment; finish is nonfoil) and 12 additional Scene Box art cards. `art_series_scope.csv` enumerates these as 120 Art Series variants. These are collectible art-card objects, not playable HOB printings. This supersedes the earlier note that the overall Art Series inventory was wholly unenumerated.
- Cardmarket Extras publicly distinguishes Art Series products by `Art Series:` product names and version suffixes; names that match HOB collector cards are art-card representations and do not create new HOB playable identities. Its page blocks direct structured extraction (HTTP 403), so a complete product-ID-level join of every Extras line to the Art Series checklist or HOB collector-number/treatment remains unverified. No Cardmarket product IDs were inferred or applied.
- `physical_scope.csv` now distinguishes physical object type (`card`, `token_face`, `helper_card`), reported finish, and treatment. For foil rows, `finish_detail` marks `surge_foil` where the Scryfall record identifies it; otherwise the precise foil technology is `traditional_foil_or_foil_unspecified` pending product collation. Wizards confirms traditional foil for the Collector Booster token and distinguishes surge-foil treatments for specific HOB card treatments.
- Art Series is represented separately in `art_series_scope.csv` because Scryfall has no Hobbit-specific Art Series set code. The scope is English, nonfoil, with Standard Art Card / Gold-Stamped treatment variants, plus the Scene Box art-card insert records.


Cardmarket Art Series listing confirms V.1/V.2 as commercial versions and classifies card records as `The Hobbit: Extras` products. Art Series name prefix keeps those separate from playable HOB cards; HOB card alternate treatments remain matched to HOB collector numbers. Exact V-number to standard/gold-stamped mapping is not established and is left unresolved.
